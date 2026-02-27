import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
from datetime import timedelta
import enum

# ==========================================
# 1. ตั้งค่า Database (เวอร์ชัน 5: Full Features)
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
    
    # รวมฟิลด์สินค้าและร้านค้ากลับมา เพื่อใช้ทำ Ranking
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
# 2. ฟังก์ชันระบบ Session
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
                else:
                    st.error("กรุณากรอกข้อมูลให้ครบ")

# ==========================================
# 4. ระบบหลัก (เมื่อ Login สำเร็จ)
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

    st.title("💼 Affiliate Farm Management System")
    
    # --- มี 5 แท็บครบถ้วน ---
    tab_dashboard, tab_txns, tab_ranking, tab_manage, tab_settings = st.tabs([
        "📊 แดชบอร์ด", "📥 บันทึกยอดขาย", "🏆 อันดับขายดี", "📝 จัดการสถานะบัญชี", "⚙️ ตั้งค่าระบบ/แชร์"
    ])
    
    viewable_accounts = get_viewable_accounts(current_user_id)
    viewable_acc_ids = [a.id for a in viewable_accounts]

    # --- แท็บ 1: แดชบอร์ดหลัก ---
    with tab_dashboard:
        st.header("📈 สรุปภาพรวมฟาร์มบัญชีของคุณ")
        if not viewable_accounts:
            st.info("คุณยังไม่มีบัญชีในระบบ ไปที่แท็บ 'ตั้งค่าระบบ' เพื่อเพิ่มบัญชีครับ")
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

    # --- แท็บ 2: บันทึกยอดขาย ---
    with tab_txns:
        st.header("📥 บันทึกจำนวนที่ขายได้และค่าคอม")
        if viewable_accounts:
            with st.form("add_txn_form"):
                acc_name = st.selectbox("เลือกบัญชี:", [a.account_name for a in viewable_accounts])
                order_id = st.text_input("รหัสออเดอร์/เลขอ้างอิง*")
                
                c_s1, c_s2 = st.columns(2)
                shop_name = c_s1.text_input("ชื่อร้านค้า (พิมพ์สั้นๆ ได้เลย)")
                shop_link = c_s2.text_input("ลิงก์ร้านค้า (ไม่บังคับ)")
                
                c_p1, c_p2 = st.columns(2)
                product_name = c_p1.text_input("ชื่อสินค้า* (เพื่อให้ขึ้นใน Ranking)")
                product_link = c_p2.text_input("ลิงก์สินค้า (ไม่บังคับ)")
                
                c_q1, c_q2 = st.columns(2)
                qty = c_q1.number_input("จำนวนที่ขายได้ (ชิ้น)*", min_value=1, value=1, step=1)
                comm = c_q2.number_input("ค่าคอมมิชชั่นรวมที่ได้ (บาท)*", min_value=0.0, step=1.0)
                
                if st.form_submit_button("💾 บันทึกยอด"):
                    if order_id and acc_name and product_name:
                        acc = session.query(AffiliateAccount).filter_by(account_name=acc_name, user_id=current_user_id).first()
                        if not acc:
                            st.error("เพิ่มยอดได้เฉพาะบัญชีที่เป็นของคุณเท่านั้น (บัญชีแชร์เพิ่มไม่ได้)")
                        else:
                            txn = TransactionRecord(
                                order_id=order_id, account_id=acc.id,
                                shop_name=shop_name, shop_link=shop_link,
                                product_name=product_name, product_link=product_link,
                                quantity=qty, commission_amount=comm
                            )
                            session.add(txn)
                            session.commit()
                            st.success(f"บันทึกยอดขายสำเร็จ!")
                    else:
                        st.error("กรุณากรอก รหัสออเดอร์ และ ชื่อสินค้า ให้ครบถ้วน")
        else:
            st.warning("ยังไม่มีบัญชีให้บันทึกยอด")

    # --- แท็บ 3: อันดับขายดี (กลับมาแล้ว!) ---
    with tab_ranking:
        st.header("🏆 จัดอันดับ 20 ร้านค้า & สินค้าขายดี")
        st.markdown("วิเคราะห์สินค้าและร้านค้า เฉพาะข้อมูลบัญชีของคุณและเพื่อนที่แชร์ให้")
        
        col_date1, col_date2 = st.columns(2)
        start_date = col_date1.date_input("ตั้งแต่หน้า", value=datetime.date.today() - timedelta(days=30))
        end_date = col_date2.date_input("ถึงวันที่", value=datetime.date.today())
        
        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max)

        st.divider()
        col_rank_shop, col_rank_prod = st.columns(2)

        # TOP 20 ร้านค้า
        with col_rank_shop:
            st.subheader("🏪 Top 20 ร้านค้าขายดี")
            top_shops = session.query(
                TransactionRecord.shop_name.label('ชื่อร้านค้า'),
                TransactionRecord.shop_link.label('ลิงก์ร้านค้า'),
                func.sum(TransactionRecord.quantity).label('จำนวนขายได้ (ชิ้น)'),
                func.sum(TransactionRecord.commission_amount).label('ค่าคอมรวม')
            ).filter(
                TransactionRecord.account_id.in_(viewable_acc_ids),
                TransactionRecord.created_at >= start_dt, TransactionRecord.created_at <= end_dt,
                TransactionRecord.shop_name != None, TransactionRecord.shop_name != ""
            ).group_by(TransactionRecord.shop_name, TransactionRecord.shop_link) \
             .order_by(func.sum(TransactionRecord.quantity).desc()).limit(20).all()

            if top_shops:
                df_shops = pd.DataFrame(top_shops)
                df_shops['ค่าคอมรวม'] = df_shops['ค่าคอมรวม'].apply(lambda x: f"฿{x:,.2f}")
                st.dataframe(
                    df_shops,
                    column_config={"ลิงก์ร้านค้า": st.column_config.LinkColumn("🔗 ลิงก์ร้านค้า")},
                    hide_index=True, use_container_width=True
                )
            else:
                st.info("ไม่มีข้อมูลร้านค้าในช่วงเวลานี้")

        # TOP 20 สินค้า
        with col_rank_prod:
            st.subheader("📦 Top 20 สินค้าขายดี")
            top_products = session.query(
                TransactionRecord.product_name.label('ชื่อสินค้า'),
                TransactionRecord.product_link.label('ลิงก์สินค้า'),
                func.sum(TransactionRecord.quantity).label('จำนวนขายได้ (ชิ้น)'),
                func.sum(TransactionRecord.commission_amount).label('ค่าคอมรวม')
            ).filter(
                TransactionRecord.account_id.in_(viewable_acc_ids),
                TransactionRecord.created_at >= start_dt, TransactionRecord.created_at <= end_dt,
                TransactionRecord.product_name != None, TransactionRecord.product_name != ""
            ).group_by(TransactionRecord.product_name, TransactionRecord.product_link) \
             .order_by(func.sum(TransactionRecord.quantity).desc()).limit(20).all()

            if top_products:
                df_prods = pd.DataFrame(top_products)
                df_prods['ค่าคอมรวม'] = df_prods['ค่าคอมรวม'].apply(lambda x: f"฿{x:,.2f}")
                st.dataframe(
                    df_prods,
                    column_config={"ลิงก์สินค้า": st.column_config.LinkColumn("🔗 ลิงก์สินค้า")},
                    hide_index=True, use_container_width=True
                )
            else:
                st.info("ไม่มีข้อมูลสินค้าในช่วงเวลานี้")

    # --- แท็บ 4: จัดการสถานะ ---
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
                     st.markdown("**สถานะ KYC**")
                     new_kyc_status = st.selectbox("เลือกสถานะ:", [e.value for e in KYCStatus], index=list(KYCStatus).index(target_acc.kyc_status))
                     default_kyc_date = target_acc.kyc_submit_date if target_acc.kyc_submit_date else datetime.date.today()
                     new_kyc_date = st.date_input("วันที่ยื่น KYC:", value=default_kyc_date)
                 with c2:
                     st.markdown("**สถานะปุ่ม Live**")
                     new_btn_status = st.selectbox("เลือกสถานะ:", [e.value for e in ButtonStatus], index=list(ButtonStatus).index(target_acc.button_status))
                     default_btn_date = target_acc.button_request_date if target_acc.button_request_date else datetime.date.today()
                     new_btn_date = st.date_input("วันที่ยื่นขอปุ่ม:", value=default_btn_date)
                 
                 if st.form_submit_button("💾 บันทึกการอัปเดต"):
                     target_acc.kyc_status = KYCStatus(new_kyc_status)
                     target_acc.kyc_submit_date = datetime.datetime.combine(new_kyc_date, datetime.datetime.min.time())
                     target_acc.button_status = ButtonStatus(new_btn_status)
                     target_acc.button_request_date = datetime.datetime.combine(new_btn_date, datetime.datetime.min.time())
                     session.commit()
                     st.success("อัปเดตข้อมูลสำเร็จ! (กรุณาเปลี่ยนแท็บเพื่อดูการเปลี่ยนแปลงในแดชบอร์ด)")

    # --- แท็บ 5: ตั้งค่าระบบและแชร์ ---
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
            
            with st.form("change_pin_form"):
                st.markdown(f"**รหัสลบปัจจุบันคือ:** `{my_user.delete_pin}`")
                new_pin = st.text_input("ตั้งรหัสลบข้อมูลใหม่", type="password")
                if st.form_submit_button("เปลี่ยนรหัสลบ"):
                    if new_pin:
                        my_user.delete_pin = new_pin
                        session.commit()
                        st.success("เปลี่ยนรหัสลบข้อมูลสำเร็จ!")
            
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
                        else:
                            st.error("รหัสลบไม่ถูกต้อง!")
