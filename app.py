import streamlit as st
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==========================================
# ⚙️ 1. ตั้งค่าฐานข้อมูล
# ==========================================
try:
    db_url = st.secrets["DB_URL"]
except:
    db_url = 'sqlite:///affiliate_farm_v5.db'

engine = create_engine(db_url, echo=False)
Base = declarative_base()

# ==========================================
# 🗄️ 2. สร้างตารางข้อมูลแบบแรกสุด (ดั้งเดิม)
# ==========================================
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    accounts = relationship("AffiliateAccount", back_populates="owner", cascade="all, delete-orphan")

class AffiliateAccount(Base):
    __tablename__ = 'affiliate_accounts'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'))
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

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# ==========================================
# 🔐 3. ระบบจัดการผู้ใช้งาน
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

def login_user(username, password):
    user = session.query(User).filter_by(username=username, password=password).first()
    if user:
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = user.id
        st.session_state['username'] = user.username
        return True
    return False

# ==========================================
# 🖥️ 4. หน้าจอหลักของแอป
# ==========================================
st.set_page_config(page_title="Affiliate Farm Dashboard", page_icon="🌾", layout="wide")

if not st.session_state['logged_in']:
    st.title("🌾 เข้าสู่ระบบ Affiliate Farm")
    tab1, tab2 = st.tabs(["🔑 เข้าสู่ระบบ", "📝 สมัครสมาชิกใหม่"])
    
    with tab1:
        with st.form("login_form"):
            log_user = st.text_input("ชื่อผู้ใช้ (Username)")
            log_pass = st.text_input("รหัสผ่าน (Password)", type="password")
            if st.form_submit_button("เข้าสู่ระบบ"):
                if login_user(log_user, log_pass):
                    st.success("เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                    
    with tab2:
        with st.form("register_form"):
            reg_user = st.text_input("ตั้งชื่อผู้ใช้ใหม่")
            reg_pass = st.text_input("ตั้งรหัสผ่าน", type="password")
            if st.form_submit_button("สมัครสมาชิก"):
                if session.query(User).filter_by(username=reg_user).first():
                    st.error("ชื่อผู้ใช้นี้มีคนใช้แล้วครับ")
                else:
                    new_user = User(username=reg_user, password=reg_pass)
                    session.add(new_user)
                    session.commit()
                    st.success("สมัครสมาชิกสำเร็จ! กลับไปเข้าสู่ระบบได้เลยครับ")

else:
    # --- เมนูด้านข้าง ---
    st.sidebar.title(f"👤 ยินดีต้อนรับ {st.session_state['username']}")
    menu = st.sidebar.radio("📌 เลือกเมนู", ["💼 จัดการบัญชี Affiliate", "📝 บันทึกยอดขายและดูรายการ"])
    
    if st.sidebar.button("🚪 ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.rerun()

    current_user = session.query(User).get(st.session_state['user_id'])

    # ------------------------------------------
    # เมนูที่ 1: จัดการบัญชีแบบดั้งเดิม
    # ------------------------------------------
    if menu == "💼 จัดการบัญชี Affiliate":
        st.title("💼 จัดการบัญชี Affiliate")
        with st.form("add_account_form"):
            acc_name = st.text_input("ชื่อบัญชีใหม่ (เช่น TikTok, FB Page)")
            if st.form_submit_button("บันทึกบัญชี"):
                if acc_name:
                    new_acc = AffiliateAccount(name=acc_name, owner_id=current_user.id)
                    session.add(new_acc)
                    session.commit()
                    st.success(f"เพิ่มบัญชี {acc_name} เรียบร้อยแล้ว!")
                    st.rerun()
                else:
                    st.error("กรุณากรอกชื่อบัญชีครับ")
        
        st.markdown("---")
        st.subheader("📋 บัญชีของคุณทั้งหมด")
        accounts = session.query(AffiliateAccount).filter_by(owner_id=current_user.id).all()
        if accounts:
            for acc in accounts:
                st.write(f"- 📌 **{acc.name}**")
        else:
            st.write("ยังไม่มีบัญชี")

    # ------------------------------------------
    # เมนูที่ 2: บันทึกยอดขายและดูรายการ
    # ------------------------------------------
    elif menu == "📝 บันทึกยอดขายและดูรายการ":
        st.title("📝 บันทึกยอดคอมมิชชันใหม่")
        accounts = session.query(AffiliateAccount).filter_by(owner_id=current_user.id).all()
        
        if not accounts:
            st.warning("⚠️ กรุณาสร้าง 'บัญชี Affiliate' ในเมนูจัดการบัญชีก่อนครับ")
        else:
            acc_dict = {acc.name: acc.id for acc in accounts}
            
            with st.form("add_transaction_form"):
                selected_acc = st.selectbox("เลือกบัญชี", list(acc_dict.keys()))
                order_id = st.text_input("รหัสคำสั่งซื้อ (Order ID)")
                product_name = st.text_input("ชื่อสินค้า")
                shop_name = st.text_input("ชื่อร้านค้า")
                quantity = st.number_input("จำนวน", min_value=1, step=1)
                commission = st.number_input("ยอดคอมมิชชันที่ได้ (บาท)", min_value=0.0, step=1.0)
                
                if st.form_submit_button("บันทึกยอด"):
                    if order_id and product_name:
                        new_trans = TransactionRecord(
                            order_id=order_id,
                            account_id=acc_dict[selected_acc],
                            product_name=product_name,
                            shop_name=shop_name,
                            quantity=quantity,
                            commission_amount=commission
                        )
                        session.add(new_trans)
                        session.commit()
                        st.success("✅ บันทึกยอดสำเร็จ!")
                        st.rerun()
                    else:
                        st.error("กรุณากรอกรหัสคำสั่งซื้อและชื่อสินค้าครับ")
            
            st.markdown("---")
            st.subheader("📋 รายการที่บันทึกไว้")
            
            has_records = False
            for acc in accounts:
                if acc.transactions:
                    has_records = True
                    st.write(f"**บัญชี: {acc.name}**")
                    for t in acc.transactions:
                        st.write(f"- 🕒 วันที่: {t.created_at.strftime('%Y-%m-%d')} | สินค้า: {t.product_name} | คอมมิชชัน: ฿{t.commission_amount:,.2f}")
            
            if not has_records:
                st.write("ยังไม่มีประวัติการบันทึกยอดขาย")
