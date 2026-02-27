import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
from datetime import timedelta
import enum

# ==========================================
# 1. ตั้งค่า Database (เวอร์ชัน 4: มีระบบ User)
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

# ตารางผู้ใช้งานระบบ
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False) 
    delete_pin = Column(String(10), default="062531") # รหัสผ่านสำหรับลบ (ตั้งค่าเองได้)
    
    accounts = relationship("AffiliateAccount", back_populates="owner", cascade="all, delete-orphan")

# ตารางเก็บสิทธิ์การแชร์ข้อมูล
class SharedAccess(Base):
    __tablename__ = 'shared_access'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    viewer_id = Column(Integer, ForeignKey('users.id'), nullable=False)

class AffiliateAccount(Base):
    __tablename__ = 'affiliate_accounts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False) # ผูกบัญชีกับ User
    account_name = Column(String(100), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    affiliate_id = Column(String(100), nullable=False)
    
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.NONE)
    kyc_submit_date = Column(DateTime, nullable=True)
    button_status = Column(Enum(ButtonStatus), default=ButtonStatus.NONE)
    button_request_date = Column(DateTime, nullable=True)
    
    owner = relationship("User", back_populates="accounts")
    transactions = relationship("TransactionRecord", back_populates="account", cascade="all, delete-orphan")

# ตารางยอดขาย (ปรับให้เรียบง่ายขึ้นตามต้องการ)
class TransactionRecord(Base):
    __tablename__ = 'transaction_records'
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), nullable=False)
    account_id = Column(Integer, ForeignKey('affiliate_accounts.id'))
    
    item_name = Column(String(255)) # เก็บแค่ชื่อ/อ้างอิง
    quantity = Column(Integer, default=1) # จำนวนที่ขายได้
    commission_amount = Column(Float, default=0.0) # ค่าคอมมิชชั่น
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    account = relationship("AffiliateAccount", back_populates="transactions")

engine = create_engine('sqlite:///affiliate_farm_v4.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# ==========================================
# 2. ฟังก์ชันระบบ Session และ User
# ==========================================
st.set_page_config(page_title="Affiliate Farm Pro (SaaS)", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['username'] = None

def calculate_days_passed(target_date):
    if not target_date: return 0
    if isinstance(target_date, datetime.date) and not isinstance(target_date, datetime.datetime):
        target_date = datetime.datetime.combine(target_date, datetime.datetime.min.time())
    return (datetime.datetime.now() - target_date).days

# ดึงบัญชีที่เป็นของ User ปัจจุบัน + บัญชีที่เพื่อนแชร์มาให้
def get_viewable_accounts(current_user_id):
    # หา ID ของคนที่แชร์ข้อมูลให้เรา
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
                        new_user = User(username=reg_user, password=reg_pass)
                        session.add(new_user)
                        session.commit()
                        st.success("สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ")
                else:
                    st.error("กรุณากรอกข้อมูลให้ครบ")

# ==========================================
# 4. ระบบหลัก (เมื่อ Login สำเร็จ)
# ==========================================
else:
    current_user_id = st.session_state['user_id']
    current_username = st.session_state['username']
    
    # เมนูด้านซ้ายสำหรับ Logout
    st.sidebar.markdown(f"👤 ยินดีต้อนรับ, **{current_username}**")
    if st.sidebar.button("🚪 ล็อกเอาท์"):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.rerun()

    st.title("💼 Affiliate Farm Management System")
    
    tab_dashboard, tab_txns, tab_manage, tab_settings = st.tabs([
        "📊 แดชบอร์ด", "📥 บันทึกยอดขาย", "📝 จัดการสถานะบัญชี", "⚙️ ตั้งค่าระบบ/แชร์"
    ])
    
    viewable_accounts = get_viewable_accounts(current_user_id)
    viewable_acc_ids = [a.id for a in viewable_accounts]

    # --- แท็บ 1: แดชบอร์ด ---
    with tab_dashboard:
        st.header("📈 สรุปภาพรวมฟาร์มบัญชีของคุณ")
        if not viewable_accounts:
            st.info("คุณยังไม่มีบัญชีในระบบ ไปที่แท็บ 'ตั้งค่าระบบ' เพื่อเพิ่มบัญชีครับ")
        else:
            total_accounts = len(viewable_accounts)
            
            # คำนวณยอดเงินและออเดอร์
            account_stats = session.query(
                AffiliateAccount.id,
                func.sum(TransactionRecord.commission_amount).label('total_comm'),
                func.sum(TransactionRecord.quantity).label('total_qty') # เปลี่ยนมานับจำนวนชิ้นรวม
            ).outerjoin(TransactionRecord).filter(AffiliateAccount.id.in_(viewable_acc_ids)).group_by(AffiliateAccount.id).all()

            acc_500_baht = sum(1 for stat in account_stats if (stat.total_comm or 0) >= 500)
            
            # สมมติเงื่อนไข 90 ออเดอร์ คือ 90 ชิ้นที่ขายได้
            acc_90_orders = sum(1 for stat in account_stats if (stat.total_qty or 0) >= 90)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📌 จำนวนบัญชีทั้งหมด", f"{total_accounts} บัญชี")
            col2.metric("🎯 บัญชีที่ค่าคอมครบ 500 บาท", f"{acc_500_baht} บัญชี")
            col3.metric("📦 บัญชีที่ขายครบ 90 ชิ้น", f"{acc_90_orders} บัญชี")

    # --- แท็บ 2: บันทึกยอดขาย (แบบเรียบง่าย) ---
    with tab_txns:
        st.header("📥 บันทึกจำนวนที่ขายได้และค่าคอม")
        if viewable_accounts:
            with st.form("add_simple_txn"):
                acc_name = st.selectbox("เลือกบัญชี:", [a.account_name for a in viewable_accounts])
                order_id = st.text_input("รหัสออเดอร์/เลขอ้างอิง*")
                item_name = st.text_input("ชื่อสินค้า (พิมพ์สั้นๆ เพื่อให้จำได้)")
                
                c1, c2 = st.columns(2)
                qty = c1.number_input("จำนวนที่ขายได้ (ชิ้น)*", min_value=1, value=1, step=1)
                comm = c2.number_input("ค่าคอมมิชชั่นรวมที่ได้ (บาท)*", min_value=0.0, step=1.0)
                
                if st.form_submit_button("💾 บันทึกยอด"):
                    if order_id and acc_name:
                        acc = session.query(AffiliateAccount).filter_by(account_name=acc_name, user_id=current_user_id).first()
                        if not acc:
                            st.error("คุณไม่สามารถเพิ่มยอดเข้าบัญชีที่ถูกแชร์มาให้ได้ (เพิ่มได้เฉพาะบัญชีตัวเอง)")
                        else:
                            txn = TransactionRecord(
                                order_id=order_id, account_id=acc.id,
                                item_name=item_name, quantity=qty, commission_amount=comm
                            )
                            session.add(txn)
                            session.commit()
                            st.success(f"บันทึกยอดขาย {qty} ชิ้น ค่าคอม {comm} บาท สำเร็จ!")
                    else:
                        st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
        else:
            st.warning("ยังไม่มีบัญชีให้บันทึกยอด")

    # --- แท็บ 3: จัดการสถานะ (ตัดมาเฉพาะส่วนสำคัญ) ---
    with tab_manage:
         st.header("📝 อัปเดตสถานะรายบัญชี")
         my_accounts = [a for a in viewable_accounts if a.user_id == current_user_id]
         if my_accounts:
             account_names = [acc.account_name for acc in my_accounts]
             selected_acc_name = st.selectbox("🔍 เลือกบัญชีที่ต้องการอัปเดต (เฉพาะของคุณ):", account_names)
             target_acc = session.query(AffiliateAccount).filter_by(account_name=selected_acc_name).first()
             
             with st.form("update_kyc_form"):
                 c1, c2 = st.columns(2)
                 with c1:
                     new_kyc_status = st.selectbox("สถานะ KYC:", [e.value for e in KYCStatus], index=list(KYCStatus).index(target_acc.kyc_status))
                 with c2:
                     new_btn_status = st.selectbox("สถานะปุ่ม Live:", [e.value for e in ButtonStatus], index=list(ButtonStatus).index(target_acc.button_status))
                 
                 if st.form_submit_button("บันทึกสถานะ"):
                     target_acc.kyc_status = KYCStatus(new_kyc_status)
                     target_acc.button_status = ButtonStatus(new_btn_status)
                     session.commit()
                     st.success("อัปเดตสำเร็จ!")

    # --- แท็บ 4: ตั้งค่า (เพิ่มบัญชี, แชร์ให้เพื่อน, เปลี่ยน PIN ลบ) ---
    with tab_settings:
        st.header("⚙️ ตั้งค่าระบบส่วนตัว")
        col_add, col_share, col_pin = st.columns(3)
        
        with col_add:
            st.subheader("➕ เพิ่มบัญชีฟาร์ม")
            with st.form("add_acc_form"):
                new_name = st.text_input("ชื่อบัญชี*")
                new_platform = st.selectbox("แพลตฟอร์ม", ["Shopee", "TikTok"])
                new_aff_id = st.text_input("Affiliate ID*")
                if st.form_submit_button("บันทึก"):
                    if new_name and new_aff_id:
                        session.add(AffiliateAccount(user_id=current_user_id, account_name=new_name, platform=PlatformEnum(new_platform), affiliate_id=new_aff_id))
                        session.commit()
                        st.success("เพิ่มบัญชีแล้ว!")
                        
        with col_share:
            st.subheader("🤝 แชร์ข้อมูลให้เพื่อน")
            st.markdown("ให้เพื่อนล็อกอินเข้ามาดูยอดของเราได้")
            with st.form("share_form"):
                friend_username = st.text_input("พิมพ์ Username ของเพื่อน")
                if st.form_submit_button("อนุญาตให้เพื่อนดูข้อมูล"):
                    friend = session.query(User).filter_by(username=friend_username).first()
                    if not friend:
                        st.error("ไม่พบ Username นี้ในระบบ")
                    elif friend.id == current_user_id:
                        st.error("แชร์ให้ตัวเองไม่ได้ครับ!")
                    else:
                        existing_share = session.query(SharedAccess).filter_by(owner_id=current_user_id, viewer_id=friend.id).first()
                        if not existing_share:
                            session.add(SharedAccess(owner_id=current_user_id, viewer_id=friend.id))
                            session.commit()
                            st.success(f"แชร์ข้อมูลให้ {friend_username} สำเร็จ!")
                        else:
                            st.info("คุณแชร์ให้คนนี้ไปแล้ว")

        with col_pin:
            st.subheader("🗑️ ลบบัญชี & รหัสผ่าน")
            my_user = session.query(User).filter_by(id=current_user_id).first()
            
            # ฟอร์มเปลี่ยนรหัส PIN สำหรับลบ
            with st.form("change_pin_form"):
                st.markdown(f"**รหัสลบปัจจุบันคือ:** `{my_user.delete_pin}`")
                new_pin = st.text_input("ตั้งรหัสลบข้อมูลใหม่", type="password")
                if st.form_submit_button("เปลี่ยนรหัสลบ"):
                    if new_pin:
                        my_user.delete_pin = new_pin
                        session.commit()
                        st.success("เปลี่ยนรหัสลบข้อมูลสำเร็จ!")
            
            st.divider()
            # ฟอร์มลบบัญชี
            my_accounts = [a for a in viewable_accounts if a.user_id == current_user_id]
            if my_accounts:
                with st.form("delete_acc_form"):
                    acc_to_delete = st.selectbox("เลือกลบบัญชี:", [a.account_name for a in my_accounts])
                    input_pin = st.text_input("ใส่รหัสเพื่อยืนยันการลบ*", type="password")
                    if st.form_submit_button("🚨 ยืนยันการลบ"):
                        if input_pin == my_user.delete_pin:
                            acc_obj = session.query(AffiliateAccount).filter_by(account_name=acc_to_delete, user_id=current_user_id).first()
                            session.delete(acc_obj)
                            session.commit()
                            st.success("ลบบัญชีสำเร็จ!")
                        else:
                            st.error("รหัสลบไม่ถูกต้อง!")
