import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
from datetime import timedelta
import enum
import time

# ==========================================
# 1. ตั้งค่า Database (V5)
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

engine = create_engine('sqlite:///affiliate_farm_v5.db', echo=False)
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
# 4. ระบบหลัก (All-in-One Dashboard)
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
    
    # ยุบรวมแท็บให้ดูสะอาดตา
    tab_dashboard, tab_ranking, tab_settings = st.tabs([
        "📊 แดชบอร์ด & จัดการบัญชี", "🏆 อันดับขายดี", "⚙️ แชร์และตั้งค่าความปลอดภัย"
    ])
    
    viewable_accounts = get_viewable_accounts(current_user_id)
    viewable_acc_ids = [a.id for a in viewable_accounts]

    # --- แท็บ 1: แดชบอร์ด & จัดการบัญชี ---
    with tab_dashboard:
        # [ฟีเจอร์ใหม่] เพิ่มบัญชีตรงหน้าแดชบอร์ด
        with st.expander("➕ คลิกที่นี่เพื่อเพิ่มบัญชีฟาร์มใหม่", expanded=False):
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

        st.divider()
        st.subheader("📈 สรุปภาพรวมฟาร์มบัญชีของคุณ")
        
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

            col1, col2, col3 = st.columns(3)
            col1.metric("📌 จำนวนบัญชีทั้งหมด", f"{total_accounts} บัญชี")
            col2.metric("🎯 บัญชีที่ค่าคอมครบ 500 บาท", f"{acc_500_baht} บัญชี")
            col3.metric("📦 บัญชีที่ขายครบ 90 ชิ้น", f"{acc_90_orders} บัญชี")
            
            st.divider()
            
            # [ฟีเจอร์ใหม่] รายชื่อบัญชีที่คลิกขยายเพื่อจัดการได้เลย
            st.subheader("📋 รายชื่อบัญชี (คลิกที่ชื่อเพื่ออัปเดตข้อมูลรายวัน)")
            my_accounts = [a for a in viewable_accounts if a.user_id == current_user_id]
            
            for acc in my_accounts:
                # คำนวณยอดปัจจุบันของบัญชีนี้
                stat = next((s for s in account_stats if s.id == acc.id), None)
                cur_comm = stat.total_comm if stat and stat.total_comm else 0.0
                cur_qty = stat.total_qty if stat and stat.total_qty else 0
                
                # กรอบรายชื่อบัญชีแบบคลิกขยายได้
                with st.expander(f"🛒 {acc.account_name} | แพลตฟอร์ม: {acc.platform.value} | ยอดปัจจุบัน: ฿{cur_comm:,.2f} ({cur_qty} ชิ้น)"):
                    
                    # แท็บย่อยสำหรับการจัดการแต่ละบัญชี
                    t_info, t_add, t_edit, t_status = st.tabs(["📊 สรุปย่อย", "📥 บันทึกยอดวันนี้", "✏️ แก้ไข/ลบยอดเก่า", "📝 อัปเดตสถานะ"])
                    
                    with t_info:
                        st.markdown(f"**สถานะ KYC:** {acc.kyc_status.value} | **สถานะปุ่ม:** {acc.button_status.value}")
                        st.progress(min(cur_comm / 500.0, 1.0), text=f"เป้าหมายเงิน: ฿{cur_comm:,.2f} / ฿500")
                        st.progress(min(cur_qty / 90.0, 1.0), text=f"เป้าหมายออเดอร์: {cur_qty} / 90 ชิ้น")

                    with t_add:
                        with st.form(f"add_txn_{acc.id}"):
                            oid = st.text_input("รหัสออเดอร์*", key=f"oid_{acc.id}")
                            p_name = st.text_input("ชื่อสินค้า*", key=f"pname_{acc.id}")
                            c1, c2 = st.columns(2)
                            qty = c1.number_input("จำนวน (ชิ้น)", min_value=1, value=1, key=f"qty_{acc.id}")
                            comm = c2.number_input("ค่าคอม (บาท)", min_value=0.0, step=1.0, key=f"comm_{acc.id}")
                            if st.form_submit_button("💾 บันทึกยอด"):
                                if oid and p_name:
                                    session.add(TransactionRecord(order_id=oid, account_id=acc.id, product_name=p_name, quantity=qty, commission_amount=comm))
                                    session.commit()
                                    st.success("บันทึกสำเร็จ!")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("กรอกรหัสและชื่อสินค้าด้วยครับ")

                    with t_edit:
                        recent_txns = session.query(TransactionRecord).filter_by(account_id=acc.id).order_by(TransactionRecord.created_at.desc()).limit(20).all()
                        if recent_txns:
                            txn_options = {f"Order: {t.order_id} | {t.product_name} (฿{t.commission_amount})": t for t in recent_txns}
                            sel_txn_label = st.selectbox("เลือกออเดอร์ที่ต้องการแก้ไข:", list(txn_options.keys()), key=f"sel_txn_{acc.id}")
                            t_edit = txn_options[sel_txn_label]
                            
                            with st.form(f"edit_txn_form_{acc.id}"):
                                e_pname = st.text_input("ชื่อสินค้า", value=t_edit.product_name, key=f"ep_{acc.id}")
                                c1, c2 = st.columns(2)
                                e_qty = c1.number_input("จำนวน", value=t_edit.quantity, key=f"eq_{acc.id}")
                                e_comm = c2.number_input("ค่าคอม", value=t_edit.commission_amount, key=f"ec_{acc.id}")
                                
                                col_s, col_d = st.columns(2)
                                if col_s.form_submit_button("💾 บันทึกแก้ไข"):
                                    t_edit.product_name = e_pname
                                    t_edit.quantity = e_qty
                                    t_edit.commission_amount = e_comm
                                    session.commit()
                                    st.success("แก้ไขสำเร็จ!")
                                    time.sleep(0.5)
                                    st.rerun()
                                if col_d.form_submit_button("🗑️ ลบออเดอร์นี้"):
                                    session.delete(t_edit)
                                    session.commit()
                                    st.warning("ลบสำเร็จ!")
                                    time.sleep(0.5)
                                    st.rerun()
                        else:
                            st.info("ยังไม่มีออเดอร์ให้แก้ไข")

                    with t_status:
                        with st.form(f"upd_stat_{acc.id}"):
                            c1, c2 = st.columns(2)
                            n_kyc = c1.selectbox("สถานะ KYC", [e.value for e in KYCStatus], index=list(KYCStatus).index(acc.kyc_status), key=f"kyc_{acc.id}")
                            n_btn = c2.selectbox("สถานะปุ่ม", [e.value for e in ButtonStatus], index=list(ButtonStatus).index(acc.button_status), key=f"btn_{acc.id}")
                            if st.form_submit_button("อัปเดตสถานะ"):
                                acc.kyc_status = KYCStatus(n_kyc)
                                acc.button_status = ButtonStatus(n_btn)
                                session.commit()
                                st.success("อัปเดตสำเร็จ!")
                                time.sleep(0.5)
                                st.rerun()

    # --- แท็บ 2: อันดับขายดี ---
    with tab_ranking:
        st.header("🏆 จัดอันดับสินค้าขายดี (เฉพาะบัญชีของคุณและเพื่อนที่แชร์มา)")
        col_date1, col_date2 = st.columns(2)
        start_date = col_date1.date_input("ตั้งแต่หน้า", value=datetime.date.today() - timedelta(days=30))
        end_date = col_date2.date_input("ถึงวันที่", value=datetime.date.today())
        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max)

        st.subheader("📦 Top 20 สินค้าขายดี")
        top_products = session.query(
            TransactionRecord.product_name.label('ชื่อสินค้า'),
            func.sum(TransactionRecord.quantity).label('จำนวนขายได้ (ชิ้น)'),
            func.sum(TransactionRecord.commission_amount).label('ค่าคอมรวม')
        ).filter(
            TransactionRecord.account_id.in_(viewable_acc_ids),
            TransactionRecord.created_at >= start_dt, TransactionRecord.created_at <= end_dt,
            TransactionRecord.product_name != None, TransactionRecord.product_name != ""
        ).group_by(TransactionRecord.product_name) \
         .order_by(func.sum(TransactionRecord.quantity).desc()).limit(20).all()

        if top_products:
            df_prods = pd.DataFrame(top_products)
            df_prods['ค่าคอมรวม'] = df_prods['ค่าคอมรวม'].apply(lambda x: f"฿{x:,.2f}")
            st.dataframe(df_prods, hide_index=True, use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลสินค้าในช่วงเวลานี้")

    # --- แท็บ 3: ตั้งค่าระบบและแชร์ ---
    with tab_settings:
        st.header("⚙️ แชร์ข้อมูลและตั้งค่าความปลอดภัย")
        col_share, col_pin = st.columns(2)
        
        with col_share:
            st.subheader("🤝 แชร์ข้อมูลให้เพื่อน")
            with st.form("share_form"):
                friend_username = st.text_input("พิมพ์ Username ของเพื่อน")
                if st.form_submit_button("อนุญาตให้เพื่อนดูข้อมูล"):
                    friend = session.query(User).filter_by(username=friend_username).first()
                    if not friend:
                        st.error("ไม่พบ Username นี้")
                    elif friend.id == current_user_id:
                        st.error("แชร์ให้ตัวเองไม่ได้!")
                    else:
                        existing = session.query(SharedAccess).filter_by(owner_id=current_user_id, viewer_id=friend.id).first()
                        if not existing:
                            session.add(SharedAccess(owner_id=current_user_id, viewer_id=friend.id))
                            session.commit()
                            st.success(f"แชร์ข้อมูลให้ {friend_username} สำเร็จ!")
                        else:
                            st.info("แชร์ให้คนนี้ไปแล้ว")

        with col_pin:
            st.subheader("🗑️ ลบบัญชี & รหัสผ่าน")
            my_user = session.query(User).filter_by(id=current_user_id).first()
            
            with st.form("change_pin_form"):
                new_pin = st.text_input("ตั้งรหัสลบข้อมูลใหม่", type="password", placeholder=f"รหัสปัจจุบัน: {my_user.delete_pin}")
                if st.form_submit_button("เปลี่ยนรหัสลบ"):
                    if new_pin:
                        my_user.delete_pin = new_pin
                        session.commit()
                        st.success("เปลี่ยนรหัสสำเร็จ!")
            
            st.divider()
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
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("รหัสลบไม่ถูกต้อง!")
