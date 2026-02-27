import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
from datetime import timedelta
import enum
import time

# ==========================================
# 1. ตั้งค่า Database (V5 - เชื่อมต่อ Google Cloud)
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

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False) 
    delete_pin = Column(String(10), default="062531")
    accounts = relationship("AffiliateAccount", back_populates="owner", cascade="all, delete-orphan")

class SharedAccess(Base):
    __tablename__ = 'shared_access'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    viewer_id = Column(Integer, ForeignKey('users.id'), nullable=False)

class AffiliateAccount(Base):
    __tablename__ = 'affiliate_accounts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    account_name = Column(String(100), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    affiliate_id = Column(String(100), nullable=False)
    
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.NONE)
    kyc_submit_date = Column(DateTime, nullable=True)
    button_status = Column(Enum(ButtonStatus), default=ButtonStatus.NONE)
    button_request_date = Column(DateTime, nullable=True)
    
    owner = relationship("User", back_populates="accounts")
    transactions = relationship("TransactionRecord", back_populates="account", cascade="all, delete-orphan")

class TransactionRecord(Base):
    __tablename__ = 'transaction_records'
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), nullable=False)
    account_id = Column(Integer, ForeignKey('affiliate_accounts.id'))
    
    product_name = Column(String(255)) 
    product_link = Column(String(500))
    shop_name = Column(String(255))
    shop_link = Column(String(500))
    
    quantity = Column(Integer, default=1) 
    commission_amount = Column(Float, default=0.0) 
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    account = relationship("AffiliateAccount", back_populates="transactions")

# ✨ จุดที่แก้ไข: ดึงลิงก์ฐานข้อมูลจาก Streamlit Secrets 
try:
    db_url = st.secrets["DB_URL"]
except:
    db_url = 'sqlite:///affiliate_farm_v5.db'

engine = create_engine(db_url, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# ==========================================
# 2. ฟังก์ชันระบบ
# ==========================================
st.set_page_config(page_title="Affiliate Farm Pro", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['username'] = None

def calculate_days_passed(target_date):
    if not target_date: return 0
    if isinstance(target_date, datetime.date) and not isinstance(target_date, datetime.datetime):
        target_date = datetime.datetime.combine(target_date, datetime.datetime.min.time())
    return (datetime.datetime.now() - target_date).days

def get_viewable_accounts(current_user_id):
    shared_owners = session.query(SharedAccess.owner_id).filter_by(viewer_id=current_user_id).all()
    owner_ids = [current_user_id] + [so[0] for so in shared_owners]
    return session.query(AffiliateAccount).filter(AffiliateAccount.user_id.in_(owner_ids)).all()

# ==========================================
# 3. หน้า Login / Register
# ==========================================
if not st.session_state['logged_in']:
    st.title("🔐 เข้าสู่ระบบ Affiliate Farm")
    tab_login, tab_register = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิกใหม่"])
    with tab_login:
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            if st.form_submit_button("ล็อกอิน"):
                user = session.query(User).filter_by(username=login_user, password=login_pass).first()
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = user.id
                    st.session_state['username'] = user.username
                    st.rerun()
                else:
                    st.error("Username หรือ Password ไม่ถูกต้อง!")
    with tab_register:
        with st.form("register_form"):
            reg_user = st.text_input("ตั้ง Username ใหม่")
            reg_pass = st.text_input("ตั้ง Password", type="password")
            if st.form_submit_button("สมัครสมาชิก"):
                if reg_user and reg_pass:
                    if session.query(User).filter_by(username=reg_user).first():
                        st.error("Username นี้มีคนใช้แล้ว!")
                    else:
                        session.add(User(username=reg_user, password=reg_pass))
                        session.commit()
                        st.success("สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ")

# ==========================================
# 4. ระบบหลัก 
# ==========================================
else:
    current_user_id = st.session_state['user_id']
    current_username = st.session_state['username']
    
    st.sidebar.markdown(f"👤 ยินดีต้อนรับ, **{current_username}**")
    if st.sidebar.button("🚪 ล็อกเอาท์"):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.rerun()

    st.title("💼 Affiliate Farm Management")
    
    tab_dashboard, tab_manage_acc, tab_ranking, tab_settings = st.tabs([
        "📊 แดชบอร์ดหลัก", "📝 อัปเดตรายบัญชี", "🏆 อันดับขายดี", "⚙️ ตั้งค่า & แชร์"
    ])
    
    viewable_accounts = get_viewable_accounts(current_user_id)
    viewable_acc_ids = [a.id for a in viewable_accounts]
    my_accounts = [a for a in viewable_accounts if a.user_id == current_user_id]

    # --- แท็บ 1: แดชบอร์ดหลัก ---
    with tab_dashboard:
        with st.expander("➕ เพิ่มบัญชีฟาร์มใหม่", expanded=False):
            with st.form("quick_add_acc"):
                c1, c2, c3 = st.columns(3)
                new_name = c1.text_input("ชื่อบัญชี*")
                new_platform = c2.selectbox("แพลตฟอร์ม", ["Shopee", "TikTok"])
                new_aff_id = c3.text_input("Affiliate ID*")
                if st.form_submit_button("✅ บันทึกบัญชีใหม่"):
                    if new_name and new_aff_id:
                        session.add(AffiliateAccount(user_id=current_user_id, account_name=new_name, platform=PlatformEnum(new_platform), affiliate_id=new_aff_id))
                        session.commit()
                        st.success("เพิ่มบัญชีสำเร็จ!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("กรุณากรอกชื่อและ ID ให้ครบ")

        st.header("📈 สรุปภาพรวมฟาร์มบัญชีของคุณ")
        if not viewable_accounts:
            st.info("ยังไม่มีบัญชีในระบบ กรุณากดเพิ่มบัญชีด้านบนครับ")
        else:
            total_accounts = len(viewable_accounts)
            account_stats = session.query(
                AffiliateAccount.id,
                func.sum(TransactionRecord.commission_amount).label('total_comm'),
                func.sum(TransactionRecord.quantity).label('total_qty') 
            ).outerjoin(TransactionRecord).filter(AffiliateAccount.id.in_(viewable_acc_ids)).group_by(AffiliateAccount.id).all()

            acc_500_baht = sum(1 for stat in account_stats if (stat.total_comm or 0) >= 500)
            acc_90_orders = sum(1 for stat in account_stats if (stat.total_qty or 0) >= 90)
            
            kyc_submitted = sum(1 for a in viewable_accounts if a.kyc_status == KYCStatus.SUBMITTED)
            kyc_approved = sum(1 for a in viewable_accounts if a.kyc_status == KYCStatus.APPROVED)
            kyc_rejected = sum(1 for a in viewable_accounts if a.kyc_status == KYCStatus.REJECTED)
            kyc_more_docs = sum(1 for a in viewable_accounts if a.kyc_status == KYCStatus.MORE_DOCS)
            
            btn_requested = sum(1 for a in viewable_accounts if a.button_status == ButtonStatus.REQUESTED)
            btn_live_heart = sum(1 for a in viewable_accounts if a.button_status == ButtonStatus.LIVE_HEART)
            btn_live_only = sum(1 for a in viewable_accounts if a.button_status == ButtonStatus.LIVE_ONLY)
            
            expedite_kyc = sum(1 for a in viewable_accounts if a.kyc_status == KYCStatus.SUBMITTED and calculate_days_passed(a.kyc_submit_date) >= 15)
            expedite_btn = sum(1 for a in viewable_accounts if a.button_status == ButtonStatus.REQUESTED and calculate_days_passed(a.button_request_date) >= 15)

            col1, col2, col3 = st.columns(3)
            col1.metric("📌 จำนวนบัญชีทั้งหมด", f"{total_accounts} บัญชี")
            col2.metric("🎯 บัญชีที่ค่าคอมครบ 500 บาท", f"{acc_500_baht} บัญชี")
            col3.metric("📦 บัญชีที่ขายครบ 90 ชิ้น", f"{acc_90_orders} บัญชี")
            
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

    # --- แท็บ 2: อัปเดตรายบัญชี (เพิ่ม Filter สถานะปุ่ม) ---
    with tab_manage_acc:
        st.header("📋 จัดการข้อมูลรายบัญชี")
        
        if not my_accounts:
            st.info("คุณยังไม่มีบัญชีให้จัดการครับ")
        else:
            # 🔍 ส่วนของ Filter ค้นหาอัปเกรด (4 คอลัมน์)
            st.subheader("🔍 ตัวกรองค้นหาบัญชี")
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            search_query = col_f1.text_input("ค้นหาด้วยชื่อบัญชี...")
            filter_platform = col_f2.selectbox("แพลตฟอร์ม:", ["ทั้งหมด", "Shopee", "TikTok"])
            filter_kyc = col_f3.selectbox("สถานะ KYC:", ["ทั้งหมด"] + [e.value for e in KYCStatus])
            filter_btn = col_f4.selectbox("สถานะปุ่ม Live:", ["ทั้งหมด"] + [e.value for e in ButtonStatus])
            
            # ทำการกรองข้อมูลตามเงื่อนไขที่เลือก
            filtered_accounts = my_accounts
            if search_query:
                filtered_accounts = [a for a in filtered_accounts if search_query.lower() in a.account_name.lower()]
            if filter_platform != "ทั้งหมด":
                filtered_accounts = [a for a in filtered_accounts if a.platform.value == filter_platform]
            if filter_kyc != "ทั้งหมด":
                filtered_accounts = [a for a in filtered_accounts if a.kyc_status.value == filter_kyc]
            if filter_btn != "ทั้งหมด":
                filtered_accounts = [a for a in filtered_accounts if a.button_status.value == filter_btn]

            st.divider()

            if not filtered_accounts:
                st.warning("ไม่พบข้อมูลบัญชีที่ตรงกับเงื่อนไขการค้นหา")
            else:
                st.markdown(f"เจอทั้งหมด **{len(filtered_accounts)}** บัญชี (คลิกที่ชื่อเพื่ออัปเดตข้อมูล)")
                
                account_stats = session.query(
                    AffiliateAccount.id,
                    func.sum(TransactionRecord.commission_amount).label('total_comm'),
                    func.sum(TransactionRecord.quantity).label('total_qty') 
                ).outerjoin(TransactionRecord).filter(AffiliateAccount.id.in_(viewable_acc_ids)).group_by(AffiliateAccount.id).all()

                for acc in filtered_accounts:
                    stat = next((s for s in account_stats if s.id == acc.id), None)
                    cur_comm = stat.total_comm if stat and stat.total_comm else 0.0
                    cur_qty = stat.total_qty if stat and stat.total_qty else 0
                    
                    with st.expander(f"🛒 {acc.account_name} | แพลตฟอร์ม: {acc.platform.value} | ยอดปัจจุบัน: ฿{cur_comm:,.2f} ({cur_qty} ชิ้น)"):
                        t_info, t_add, t_edit, t_status = st.tabs(["📊 สรุปย่อย", "📥 บันทึกยอดวันนี้", "✏️ แก้ไข/ลบยอดเก่า", "📝 อัปเดตสถานะ"])
                        
                        with t_info:
                            st.markdown("##### 💰 สรุปยอดขายปัจจุบัน")
                            c_info1, c_info2 = st.columns(2)
                            c_info1.metric("ยอดคอมมิชชั่นสะสม", f"฿{cur_comm:,.2f}")
                            c_info2.metric("จำนวนออเดอร์สะสม", f"{cur_qty} ชิ้น")

                            st.progress(min(cur_comm / 500.0, 1.0), text=f"เป้าหมายเงิน: ฿{cur_comm:,.2f} / ฿500")
                            st.progress(min(cur_qty / 90.0, 1.0), text=f"เป้าหมายออเดอร์: {cur_qty} / 90 ชิ้น")
                            
                            st.divider()
                            st.markdown("##### 🛡️ สถานะการยืนยันตัวตนและปุ่ม Live")
                            
                            kyc_date_text = ""
                            if acc.kyc_status != KYCStatus.NONE and acc.kyc_submit_date:
                                days_kyc = calculate_days_passed(acc.kyc_submit_date)
                                kyc_date_text = f" *(ยื่นเมื่อ: {acc.kyc_submit_date.strftime('%d/%m/%Y')} - ผ่านมาแล้ว {days_kyc} วัน)*"
                                
                            btn_date_text = ""
                            if acc.button_status != ButtonStatus.NONE and acc.button_request_date:
                                days_btn = calculate_days_passed(acc.button_request_date)
                                btn_date_text = f" *(ขอเมื่อ: {acc.button_request_date.strftime('%d/%m/%Y')} - ผ่านมาแล้ว {days_btn} วัน)*"

                            st.markdown(f"- **สถานะ KYC:** {acc.kyc_status.value}{kyc_date_text}")
                            st.markdown(f"- **สถานะปุ่ม Live:** {acc.button_status.value}{btn_date_text}")

                        with t_add:
                            with st.form(f"add_txn_{acc.id}"):
                                oid = st.text_input("รหัสออเดอร์*", key=f"oid_{acc.id}")
                                c_s1, c_s2 = st.columns(2)
                                s_name = c_s1.text_input("ชื่อร้านค้า", key=f"sname_{acc.id}")
                                p_name = c_s2.text_input("ชื่อสินค้า*", key=f"pname_{acc.id}")
                                c1, c2 = st.columns(2)
                                qty = c1.number_input("จำนวน (ชิ้น)", min_value=1, value=1, key=f"qty_{acc.id}")
                                comm = c2.number_input("ค่าคอมรวม (บาท)", min_value=0.0, step=1.0, key=f"comm_{acc.id}")
                                if st.form_submit_button("💾 บันทึกยอด"):
                                    if oid and p_name:
                                        session.add(TransactionRecord(order_id=oid, account_id=acc.id, shop_name=s_name, product_name=p_name, quantity=qty, commission_amount=comm))
                                        session.commit()
                                        st.success("บันทึกสำเร็จ!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("กรอกรหัสออเดอร์และชื่อสินค้าด้วยครับ")

                        with t_edit:
                            recent_txns = session.query(TransactionRecord).filter_by(account_id=acc.id).order_by(TransactionRecord.created_at.desc()).limit(20).all()
                            if recent_txns:
                                txn_options = {f"Order: {t.order_id} | {t.product_name} (฿{t.commission_amount})": t for t in recent_txns}
                                sel_txn_label = st.selectbox("เลือกออเดอร์ที่ต้องการแก้ไข:", list(txn_options.keys()), key=f"sel_txn_{acc.id}")
                                t_edit = txn_options[sel_txn_label]
                                
                                with st.form(f"edit_txn_form_{acc.id}"):
                                    c_e1, c_e2 = st.columns(2)
                                    e_sname = c_e1.text_input("ชื่อร้านค้า", value=t_edit.shop_name or "", key=f"es_{acc.id}")
                                    e_pname = c_e2.text_input("ชื่อสินค้า", value=t_edit.product_name or "", key=f"ep_{acc.id}")
                                    c1, c2 = st.columns(2)
                                    e_qty = c1.number_input("จำนวน", value=t_edit.quantity, key=f"eq_{acc.id}")
                                    e_comm = c2.number_input("ค่าคอม", value=t_edit.commission_amount, key=f"ec_{acc.id}")
                                    
                                    col_s, col_d = st.columns(2)
                                    if col_s
