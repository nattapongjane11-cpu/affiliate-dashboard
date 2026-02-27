import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
import enum

# ==========================================
# 1. ตั้งค่า Database และโครงสร้างใหม่
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
    
    # ฟิลด์ใหม่สำหรับเก็บสถานะต่างๆ
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.NONE)
    kyc_submit_date = Column(DateTime, nullable=True) # วันที่ยื่น KYC
    
    button_status = Column(Enum(ButtonStatus), default=ButtonStatus.NONE)
    button_request_date = Column(DateTime, nullable=True) # วันที่ขอปุ่ม
    
    transactions = relationship("TransactionRecord", back_populates="account", cascade="all, delete-orphan")

class TransactionRecord(Base):
    __tablename__ = 'transaction_records'
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), unique=True, nullable=False)
    account_id = Column(Integer, ForeignKey('affiliate_accounts.id'))
    product_name = Column(String(255))
    shop_name = Column(String(255))
    sale_amount = Column(Float, default=0.0)
    commission_amount = Column(Float, default=0.0)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    account = relationship("AffiliateAccount", back_populates="transactions")

# เปลี่ยนชื่อ DB เป็น v2 เพื่อสร้างตารางใหม่ที่มีคอลัมน์ครบถ้วน
engine = create_engine('sqlite:///affiliate_farm_v2.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# ==========================================
# 2. ฟังก์ชันอำนวยความสะดวก
# ==========================================
def get_all_accounts():
    return session.query(AffiliateAccount).all()

def calculate_days_passed(target_date):
    if not target_date:
        return 0
    # แปลง datetime.date ให้เป็น datetime.datetime สำหรับคำนวณ
    if isinstance(target_date, datetime.date) and not isinstance(target_date, datetime.datetime):
        target_date = datetime.datetime.combine(target_date, datetime.datetime.min.time())
    return (datetime.datetime.now() - target_date).days

# ==========================================
# 3. ส่วนแสดงผล UI (Streamlit)
# ==========================================
st.set_page_config(page_title="Affiliate Farm Pro", layout="wide")
st.title("💼 Affiliate Farm Management System")

# แบ่งหน้าจอเป็น 3 แท็บหลัก
tab_dashboard, tab_manage, tab_settings = st.tabs(["📊 แดชบอร์ดหลัก", "📝 จัดการสถานะรายบัญชี", "⚙️ เพิ่ม/ลบบัญชี"])

# ------------------------------------------
# แท็บ 1: แดชบอร์ดหลัก (สรุปภาพรวมทั้งหมด)
# ------------------------------------------
with tab_dashboard:
    st.header("📈 สรุปภาพรวมฟาร์มบัญชี")
    
    accounts = get_all_accounts()
    total_accounts = len(accounts)
    
    # --- คำนวณยอดเงินและออเดอร์อัตโนมัติ ---
    account_stats = session.query(
        AffiliateAccount.id,
        func.sum(TransactionRecord.commission_amount).label('total_comm'),
        func.count(TransactionRecord.id).label('total_orders')
    ).outerjoin(TransactionRecord).group_by(AffiliateAccount.id).all()

    acc_500_baht = sum(1 for stat in account_stats if (stat.total_comm or 0) >= 500)
    acc_90_orders = sum(1 for stat in account_stats if (stat.total_orders or 0) >= 90)
    
    # --- คำนวณสถานะ KYC และ ปุ่ม ---
    kyc_submitted = sum(1 for a in accounts if a.kyc_status == KYCStatus.SUBMITTED)
    kyc_approved = sum(1 for a in accounts if a.kyc_status == KYCStatus.APPROVED)
    kyc_rejected = sum(1 for a in accounts if a.kyc_status == KYCStatus.REJECTED)
    kyc_more_docs = sum(1 for a in accounts if a.kyc_status == KYCStatus.MORE_DOCS)
    
    btn_requested = sum(1 for a in accounts if a.button_status == ButtonStatus.REQUESTED)
    btn_live_heart = sum(1 for a in accounts if a.button_status == ButtonStatus.LIVE_HEART)
    btn_live_only = sum(1 for a in accounts if a.button_status == ButtonStatus.LIVE_ONLY)
    
    # --- คำนวณการเร่ง (เกิน 15 วัน) ---
    expedite_kyc = sum(1 for a in accounts if a.kyc_status == KYCStatus.SUBMITTED and calculate_days_passed(a.kyc_submit_date) >= 15)
    expedite_btn = sum(1 for a in accounts if a.button_status == ButtonStatus.REQUESTED and calculate_days_passed(a.button_request_date) >= 15)

    # วาดหน้าจอ Dashboard สวยๆ แบ่งเป็นกล่องๆ
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
# แท็บ 2: จัดการสถานะรายบัญชี (อัปเดตข้อมูล)
# ------------------------------------------
with tab_manage:
    st.header("📝 อัปเดตสถานะรายบัญชี")
    accounts = get_all_accounts()
    
    if not accounts:
        st.info("ยังไม่มีบัญชีในระบบ กรุณาไปที่แท็บ 'เพิ่ม/ลบบัญชี'")
    else:
        # เลือกบัญชีที่จะแก้ไข
        account_names = [acc.account_name for acc in accounts]
        selected_acc_name = st.selectbox("🔍 เลือกบัญชีที่ต้องการอัปเดต:", account_names)
        
        # ดึงข้อมูลบัญชีที่เลือกมาแสดง
        target_acc = session.query(AffiliateAccount).filter_by(account_name=selected_acc_name).first()
        
        with st.form("update_status_form"):
            st.markdown(f"**กำลังแก้ไขบัญชี:** `{target_acc.account_name}` ({target_acc.platform.value})")
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("**สถานะ KYC**")
                new_kyc_status = st.selectbox("เลือกสถานะ KYC:", [e.value for e in KYCStatus], index=list(KYCStatus).index(target_acc.kyc_status))
                # จัดการวันที่ (ถ้ามีค่าให้แสดงค่านั้น ถ้าไม่มีให้ใช้วันนี้)
                default_kyc_date = target_acc.kyc_submit_date if target_acc.kyc_submit_date else datetime.date.today()
                new_kyc_date = st.date_input("วันที่ยื่น KYC:", value=default_kyc_date)
                
            with c2:
                st.write("**สถานะปุ่ม Live**")
                new_btn_status = st.selectbox("เลือกสถานะปุ่ม:", [e.value for e in ButtonStatus], index=list(ButtonStatus).index(target_acc.button_status))
                default_btn_date = target_acc.button_request_date if target_acc.button_request_date else datetime.date.today()
                new_btn_date = st.date_input("วันที่ยื่นขอปุ่ม:", value=default_btn_date)
            
            submit_update = st.form_submit_button("💾 บันทึกการอัปเดต")
            
            if submit_update:
                # อัปเดตข้อมูลลง Database
                target_acc.kyc_status = KYCStatus(new_kyc_status)
                target_acc.kyc_submit_date = datetime.datetime.combine(new_kyc_date, datetime.datetime.min.time())
                target_acc.button_status = ButtonStatus(new_btn_status)
                target_acc.button_request_date = datetime.datetime.combine(new_btn_date, datetime.datetime.min.time())
                
                session.commit()
                st.success("อัปเดตข้อมูลสำเร็จ! (กรุณารีเฟรชหน้าเว็บหรือเปลี่ยนแท็บเพื่อดูข้อมูลใหม่)")

# ------------------------------------------
# แท็บ 3: ตั้งค่า เพิ่ม/ลบ บัญชี
# ------------------------------------------
with tab_settings:
    col_add, col_del = st.columns(2)
    
    with col_add:
        st.header("➕ เพิ่มบัญชีใหม่")
        with st.form("add_account_form", clear_on_submit=True):
            new_name = st.text_input("ชื่อบัญชี (Account Name)*")
            new_platform = st.selectbox("แพลตฟอร์ม", ["Shopee", "TikTok"])
            new_aff_id = st.text_input("Affiliate ID / รหัสอ้างอิง*")
            
            submit_add = st.form_submit_button("บันทึกบัญชีใหม่")
            if submit_add:
                if new_name and new_aff_id:
                    # เช็คว่า ID ซ้ำไหม
                    exists = session.query(AffiliateAccount).filter_by(affiliate_id=new_aff_id).first()
                    if exists:
                        st.error("รหัส Affiliate ID นี้มีในระบบแล้ว!")
                    else:
                        new_acc = AffiliateAccount(
                            account_name=new_name,
                            platform=PlatformEnum(new_platform),
                            affiliate_id=new_aff_id
                        )
                        session.add(new_acc)
                        session.commit()
                        st.success(f"เพิ่มบัญชี {new_name} สำเร็จ!")
                else:
                    st.error("กรุณากรอกชื่อบัญชีและ Affiliate ID ให้ครบถ้วน")
                    
    with col_del:
        st.header("🗑️ ลบบัญชี")
        accounts = get_all_accounts()
        if accounts:
            with st.form("delete_account_form"):
                acc_to_delete = st.selectbox("เลือบัญชีที่ต้องการลบ (ลบแล้วกู้คืนไม่ได้):", [acc.account_name for acc in accounts])
                delete_pin = st.text_input("รหัสยืนยันการลบ*", type="password", placeholder="ใส่รหัสผ่านเพื่อลบ")
                
                submit_delete = st.form_submit_button("🚨 ยืนยันการลบบัญชี")
                if submit_delete:
                    if delete_pin == "062531":
                        acc_obj = session.query(AffiliateAccount).filter_by(account_name=acc_to_delete).first()
                        session.delete(acc_obj)
                        session.commit()
                        st.success(f"ลบบัญชี {acc_to_delete} สำเร็จเรียบร้อยแล้ว!")
                    else:
                        st.error("รหัสผ่านไม่ถูกต้อง! ไม่อนุญาตให้ลบ")
