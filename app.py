import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
from datetime import timedelta
import enum
import random

# ==========================================
# 1. ตั้งค่า Database และโครงสร้างใหม่ (v3)
# ==========================================
Base = declarative_base()

class PlatformEnum(enum.Enum):
    SHOPEE = "Shopee"
    TIKTOK = "TikTok"

class KYCStatus(enum.Enum):
    NONE = "ยังไม่ยื่น"
    SUBMITTED = "ยื่น KYC"
    APPROVED = "KYC อนุมัติ"
    REJECTED = "KYC ไม่อนุมัติ"
    MORE_DOCS = "ยื่นเอกสารเพิ่ม"

class ButtonStatus(enum.Enum):
    NONE = "ยังไม่ขอ"
    REQUESTED = "ยื่นขอปุ่ม"
    LIVE_HEART = "ได้ปุ่ม Live+หัวใจ"
    LIVE_ONLY = "ได้แต่ปุ่ม Live"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"

class AffiliateAccount(Base):
    __tablename__ = 'affiliate_accounts'
    id = Column(Integer, primary_key=True)
    account_name = Column(String(100), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    affiliate_id = Column(String(100), unique=True, nullable=False)
    
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.NONE)
    kyc_submit_date = Column(DateTime, nullable=True)
    
    button_status = Column(Enum(ButtonStatus), default=ButtonStatus.NONE)
    button_request_date = Column(DateTime, nullable=True)
    
    transactions = relationship("TransactionRecord", back_populates="account", cascade="all, delete-orphan")

class TransactionRecord(Base):
    __tablename__ = 'transaction_records'
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), unique=True, nullable=False)
    account_id = Column(Integer, ForeignKey('affiliate_accounts.id'))
    
    product_name = Column(String(255))
    product_link = Column(String(500)) # เพิ่มลิงก์สินค้า
    
    shop_name = Column(String(255))
    shop_link = Column(String(500)) # เพิ่มลิงก์ร้านค้า
    
    sale_amount = Column(Float, default=0.0)
    commission_amount = Column(Float, default=0.0)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    account = relationship("AffiliateAccount", back_populates="transactions")

engine = create_engine('sqlite:///affiliate_farm_v3.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# ==========================================
# 2. ฟังก์ชันอำนวยความสะดวก & ข้อมูลจำลอง
# ==========================================
DUMMY_SHOPS = [
    {"name": "GadgetZ", "link": "https://shopee.co.th/gadgetz"},
    {"name": "HomeDecor Hub", "link": "https://shopee.co.th/homedecor"},
    {"name": "Beauty Store", "link": "https://shopee.co.th/beautystore"},
    {"name": "Fashion BKK", "link": "https://shopee.co.th/fashionbkk"}
]

DUMMY_PRODUCTS = [
    {"name": "หูฟังบลูทูธ 5.0", "link": "https://shopee.co.th/p1"},
    {"name": "พาวเวอร์แบงค์ 20000mAh", "link": "https://shopee.co.th/p2"},
    {"name": "กล่องเก็บของมินิมอล", "link": "https://shopee.co.th/p3"},
    {"name": "โคมไฟตั้งโต๊ะ LED", "link": "https://shopee.co.th/p4"},
    {"name": "เซรั่มวิตามินซี", "link": "https://shopee.co.th/p5"}
]

def seed_dummy_data():
    if session.query(AffiliateAccount).count() == 0:
        acc1 = AffiliateAccount(account_name="Shopee_Main_01", platform=PlatformEnum.SHOPEE, affiliate_id="SHP001")
        acc2 = AffiliateAccount(account_name="Shopee_Sub_02", platform=PlatformEnum.SHOPEE, affiliate_id="SHP002")
        session.add_all([acc1, acc2])
        session.commit()

        # สร้างออเดอร์โดยสุ่มวันที่ย้อนหลังไป 1-45 วัน
        for i in range(150):
            shop = random.choice(DUMMY_SHOPS)
            product = random.choice(DUMMY_PRODUCTS)
            random_days_ago = random.randint(0, 45)
            past_date = datetime.datetime.now() - timedelta(days=random_days_ago)
            
            txn = TransactionRecord(
                order_id=f"ORD_{i}", 
                account_id=random.choice([acc1.id, acc2.id]), 
                product_name=product["name"],
                product_link=product["link"],
                shop_name=shop["name"],
                shop_link=shop["link"],
                commission_amount=random.uniform(5.0, 30.0), 
                status=OrderStatus.APPROVED,
                created_at=past_date
            )
            session.add(txn)
        session.commit()

seed_dummy_data()

def get_all_accounts():
    return session.query(AffiliateAccount).all()

def calculate_days_passed(target_date):
    if not target_date:
        return 0
    if isinstance(target_date, datetime.date) and not isinstance(target_date, datetime.datetime):
        target_date = datetime.datetime.combine(target_date, datetime.datetime.min.time())
    return (datetime.datetime.now() - target_date).days

# ==========================================
# 3. ส่วนแสดงผล UI (Streamlit)
# ==========================================
st.set_page_config(page_title="Affiliate Farm Pro", layout="wide")
st.title("💼 Affiliate Farm Management System")

# เพิ่มแท็บที่ 4 สำหรับดู Ranking โดยเฉพาะ
tab_dashboard, tab_manage, tab_settings, tab_ranking = st.tabs(["📊 แดชบอร์ดหลัก", "📝 จัดการสถานะรายบัญชี", "⚙️ เพิ่ม/ลบบัญชี", "🏆 ร้านค้า/สินค้าขายดี"])

# ------------------------------------------
# แท็บ 1: แดชบอร์ดหลัก (เหมือนเดิม)
# ------------------------------------------
with tab_dashboard:
    st.header("📈 สรุปภาพรวมฟาร์มบัญชี")
    accounts = get_all_accounts()
    total_accounts = len(accounts)
    
    account_stats = session.query(
        AffiliateAccount.id,
        func.sum(TransactionRecord.commission_amount).label('total_comm'),
        func.count(TransactionRecord.id).label('total_orders')
    ).outerjoin(TransactionRecord).group_by(AffiliateAccount.id).all()

    acc_500_baht = sum(1 for stat in account_stats if (stat.total_comm or 0) >= 500)
    acc_90_orders = sum(1 for stat in account_stats if (stat.total_orders or 0) >= 90)
    
    kyc_submitted = sum(1 for a in accounts if a.kyc_status == KYCStatus.SUBMITTED)
    kyc_approved = sum(1 for a in accounts if a.kyc_status == KYCStatus.APPROVED)
    kyc_rejected = sum(1 for a in accounts if a.kyc_status == KYCStatus.REJECTED)
    kyc_more_docs = sum(1 for a in accounts if a.kyc_status == KYCStatus.MORE_DOCS)
    
    btn_requested = sum(1 for a in accounts if a.button_status == ButtonStatus.REQUESTED)
    btn_live_heart = sum(1 for a in accounts if a.button_status == ButtonStatus.LIVE_HEART)
    btn_live_only = sum(1 for a in accounts if a.button_status == ButtonStatus.LIVE_ONLY)
    
    expedite_kyc = sum(1 for a in accounts if a.kyc_status == KYCStatus.SUBMITTED and calculate_days_passed(a.kyc_submit_date) >= 15)
    expedite_btn = sum(1 for a in accounts if a.button_status == ButtonStatus.REQUESTED and calculate_days_passed(a.button_request_date) >= 15)

    col1, col2, col3 = st.columns(3)
    col1.metric("📌 จำนวนบัญชีทั้งหมด", f"{total_accounts} บัญชี")
    col2.metric("🎯 บัญชีที่ค่าคอมครบ 500 บาท", f"{acc_500_baht} บัญชี", "สำเร็จอัตโนมัติ")
    col3.metric("📦 บัญชีที่ครบ 90 ออเดอร์", f"{acc_90_orders} บัญชี", "สำเร็จอัตโนมัติ")
    
    st.divider()
    col4, col5 = st.columns(2)
    with col4:
        st.subheader("🛡️ สถานะ KYC")
        st.info(f"ยื่น KYC แล้ว: **{kyc_submitted}** บัญชี")
        st.success(f"KYC อนุมัติ: **{kyc_approved}** บัญชี")
        st.error(f"KYC ไม่อนุมัติ: **{kyc_rejected}** บัญชี")
        st.warning(f"ยื่นเอกสารเพิ่ม: **{kyc_more_docs}** บัญชี")
        
    with col5:
        st.subheader("🔴 สถานะขอปุ่ม Live")
        st.info(f"ยื่นขอปุ่ม: **{btn_requested}** บัญชี")
        st.success(f"ได้ปุ่ม Live + หัวใจ: **{btn_live_heart}** บัญชี")
        st.warning(f"ได้แต่ปุ่ม Live: **{btn_live_only}** บัญชี")
        
    st.divider()
    st.subheader("🚨 แจ้งเตือน: บัญชีที่ต้องติดตามด่วน (เกิน 15 วัน)")
    col6, col7 = st.columns(2)
    col6.error(f"⚠️ บัญชีเร่ง KYC: **{expedite_kyc}** บัญชี")
    col7.error(f"⚠️ บัญชีเร่งปุ่ม Live: **{expedite_btn}** บัญชี")

# ------------------------------------------
# แท็บ 2 & 3: จัดการสถานะ และ ตั้งค่า (เหมือนเดิม)
# ------------------------------------------
with tab_manage:
    st.header("📝 อัปเดตสถานะรายบัญชี")
    # ... (ส่วนจัดการสถานะเหมือนโค้ดชุดก่อนหน้า)
    accounts = get_all_accounts()
    if accounts:
        account_names = [acc.account_name for acc in accounts]
        selected_acc_name = st.selectbox("🔍 เลือกบัญชีที่ต้องการอัปเดต:", account_names)
        target_acc = session.query(AffiliateAccount).filter_by(account_name=selected_acc_name).first()
        with st.form("update_status_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_kyc_status = st.selectbox("เลือกสถานะ KYC:", [e.value for e in KYCStatus], index=list(KYCStatus).index(target_acc.kyc_status))
                default_kyc_date = target_acc.kyc_submit_date if target_acc.kyc_submit_date else datetime.date.today()
                new_kyc_date = st.date_input("วันที่ยื่น KYC:", value=default_kyc_date)
            with c2:
                new_btn_status = st.selectbox("เลือกสถานะปุ่ม:", [e.value for e in ButtonStatus], index=list(ButtonStatus).index(target_acc.button_status))
                default_btn_date = target_acc.button_request_date if target_acc.button_request_date else datetime.date.today()
                new_btn_date = st.date_input("วันที่ยื่นขอปุ่ม:", value=default_btn_date)
            if st.form_submit_button("💾 บันทึกการอัปเดต"):
                target_acc.kyc_status = KYCStatus(new_kyc_status)
                target_acc.kyc_submit_date = datetime.datetime.combine(new_kyc_date, datetime.datetime.min.time())
                target_acc.button_status = ButtonStatus(new_btn_status)
                target_acc.button_request_date = datetime.datetime.combine(new_btn_date, datetime.datetime.min.time())
                session.commit()
                st.success("อัปเดตข้อมูลสำเร็จ!")

with tab_settings:
    col_add, col_del = st.columns(2)
    with col_add:
        st.header("➕ เพิ่มบัญชีใหม่")
        with st.form("add_account_form", clear_on_submit=True):
            new_name = st.text_input("ชื่อบัญชี (Account Name)*")
            new_platform = st.selectbox("แพลตฟอร์ม", ["Shopee", "TikTok"])
            new_aff_id = st.text_input("Affiliate ID / รหัสอ้างอิง*")
            if st.form_submit_button("บันทึกบัญชีใหม่"):
                if new_name and new_aff_id:
                    if not session.query(AffiliateAccount).filter_by(affiliate_id=new_aff_id).first():
                        session.add(AffiliateAccount(account_name=new_name, platform=PlatformEnum(new_platform), affiliate_id=new_aff_id))
                        session.commit()
                        st.success(f"เพิ่มบัญชีสำเร็จ!")
                    else:
                        st.error("รหัสนี้มีในระบบแล้ว!")
    with col_del:
        st.header("🗑️ ลบบัญชี")
        accounts = get_all_accounts()
        if accounts:
            with st.form("delete_account_form"):
                acc_to_delete = st.selectbox("เลือกบัญชีที่ต้องการลบ:", [acc.account_name for acc in accounts])
                delete_pin = st.text_input("รหัสยืนยันการลบ*", type="password")
                if st.form_submit_button("🚨 ยืนยันการลบบัญชี"):
                    if delete_pin == "062531":
                        acc_obj = session.query(AffiliateAccount).filter_by(account_name=acc_to_delete).first()
                        session.delete(acc_obj)
                        session.commit()
                        st.success("ลบบัญชีสำเร็จ!")
                    else:
                        st.error("รหัสผ่านไม่ถูกต้อง!")

# ------------------------------------------
# แท็บ 4: 🏆 สถิติร้านค้าและสินค้าขายดี (ระบบใหม่!)
# ------------------------------------------
with tab_ranking:
    st.header("🏆 จัดอันดับ 20 ร้านค้า & สินค้าขายดี")
    st.markdown("วิเคราะห์ทิศทางสินค้าเพื่อนำไปทำคอนเทนต์ต่อ")
    
    # --- ตัวกรองช่วงเวลา ---
    st.subheader("📅 เลือกช่วงเวลาที่ต้องการดู")
    col_date1, col_date2 = st.columns(2)
    # ค่าเริ่มต้นคือดูย้อนหลัง 30 วัน
    start_date = col_date1.date_input("ตั้งแต่หน้า", value=datetime.date.today() - timedelta(days=30))
    end_date = col_date2.date_input("ถึงวันที่", value=datetime.date.today())
    
    # แปลงวันที่เพื่อใช้ดึงใน Database
    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(end_date, datetime.time.max)

    st.divider()
    col_rank_shop, col_rank_prod = st.columns(2)

    # === 1. TOP 20 ร้านค้าขายดี ===
    with col_rank_shop:
        st.subheader("🏪 Top 20 ร้านค้าขายดี")
        top_shops = session.query(
            TransactionRecord.shop_name.label('ชื่อร้านค้า'),
            TransactionRecord.shop_link.label('ลิงก์ร้านค้า'),
            func.count(TransactionRecord.id).label('จำนวนขายได้ (ครั้ง)'),
            func.sum(TransactionRecord.commission_amount).label('ค่าคอมรวม')
        ).filter(
            TransactionRecord.created_at >= start_dt,
            TransactionRecord.created_at <= end_dt,
            TransactionRecord.shop_name != None
        ).group_by(TransactionRecord.shop_name, TransactionRecord.shop_link) \
         .order_by(func.count(TransactionRecord.id).desc()).limit(20).all()

        if top_shops:
            df_shops = pd.DataFrame(top_shops)
            df_shops['ค่าคอมรวม'] = df_shops['ค่าคอมรวม'].apply(lambda x: f"฿{x:,.2f}")
            
            # ตั้งค่าให้คอลัมน์ลิงก์ สามารถคลิกเปิดแท็บใหม่ได้
            st.dataframe(
                df_shops,
                column_config={
                    "ลิงก์ร้านค้า": st.column_config.LinkColumn("🔗 ลิงก์ร้านค้า (คลิก)"),
                    "จำนวนขายได้ (ครั้ง)": st.column_config.NumberColumn("ยอดขาย (ชิ้น)"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("ไม่มีข้อมูลการขายร้านค้าในช่วงเวลานี้")

    # === 2. TOP 20 สินค้าขายดี ===
    with col_rank_prod:
        st.subheader("📦 Top 20 สินค้าขายดี")
        top_products = session.query(
            TransactionRecord.product_name.label('ชื่อสินค้า'),
            TransactionRecord.product_link.label('ลิงก์สินค้า'),
            func.count(TransactionRecord.id).label('จำนวนขายได้ (ครั้ง)'),
            func.sum(TransactionRecord.commission_amount).label('ค่าคอมรวม')
        ).filter(
            TransactionRecord.created_at >= start_dt,
            TransactionRecord.created_at <= end_dt,
            TransactionRecord.product_name != None
        ).group_by(TransactionRecord.product_name, TransactionRecord.product_link) \
         .order_by(func.count(TransactionRecord.id).desc()).limit(20).all()

        if top_products:
            df_prods = pd.DataFrame(top_products)
            df_prods['ค่าคอมรวม'] = df_prods['ค่าคอมรวม'].apply(lambda x: f"฿{x:,.2f}")
            
            st.dataframe(
                df_prods,
                column_config={
                    "ลิงก์สินค้า": st.column_config.LinkColumn("🔗 ลิงก์สินค้า (คลิก)"),
                    "จำนวนขายได้ (ครั้ง)": st.column_config.NumberColumn("ยอดขาย (ชิ้น)"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("ไม่มีข้อมูลการขายสินค้าในช่วงเวลานี้")
