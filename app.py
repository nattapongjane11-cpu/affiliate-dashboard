import streamlit as st
import pandas as pd
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==========================================
# ⚙️ 1. ตั้งค่าฐานข้อมูล (Database Setup)
# ==========================================
try:
    db_url = st.secrets["DB_URL"]
except:
    db_url = 'sqlite:///affiliate_farm_v5.db'

engine = create_engine(db_url, echo=False)
Base = declarative_base()

# ==========================================
# 🗄️ 2. สร้างตารางข้อมูล (Models)
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
    fb_ads_cost = Column(Float, default=0.0) # เพิ่มค่า Ads FB
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

# สร้างตารางในฐานข้อมูล (ให้บรรทัดนี้อยู่ต่อท้ายโค้ดด้านบนนะครับ)
Base.metadata.create_all(engine)
# สร้างตารางในฐานข้อมูล (ถ้ายังไม่มี)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# [ทริคพิเศษ] บังคับเพิ่มคอลัมน์ fb_ads_cost เผื่อตารางเก่าไม่มี
try:
    session.execute(text("ALTER TABLE affiliate_accounts ADD COLUMN fb_ads_cost FLOAT DEFAULT 0.0;"))
    session.commit()
except:
    session.rollback()

# ==========================================
# 🔐 3. ระบบจัดการผู้ใช้งาน (Session & Auth)
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
# 🖥️ 4. หน้าจอหลักของแอป (UI)
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
    # --- เมนูด้านข้าง (Sidebar) ---
    st.sidebar.title(f"👤 ยินดีต้อนรับคุณ {st.session_state['username']}")
    menu = st.sidebar.radio("📌 เลือกเมนูทำงาน", ["📊 Dashboard ภาพรวม", "💼 จัดการบัญชี (เพิ่มค่า Ads)", "📝 บันทึกยอดขาย"])
    
    if st.sidebar.button("🚪 ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.rerun()

    # ดึงข้อมูล User ปัจจุบัน
    current_user = session.query(User).get(st.session_state['user_id'])

    # ------------------------------------------
    # เมนูที่ 1: Dashboard สรุปกำไร-ขาดทุน
    # ------------------------------------------
    if menu == "📊 Dashboard ภาพรวม":
        st.title("📊 สรุปสถิติและกำไร-ขาดทุน")
        accounts = session.query(AffiliateAccount).filter_by(owner_id=current_user.id).all()
        
        if accounts:
            total_comm = 0.0
            total_ads = 0.0
            acc_data = []
            transaction_data = []

            for acc in accounts:
                acc_comm = sum([t.commission_amount for t in acc.transactions])
                acc_ads = acc.fb_ads_cost or 0.0
                acc_profit = acc_comm - acc_ads
                
                total_comm += acc_comm
                total_ads += acc_ads
                
                acc_data.append({
                    "ชื่อบัญชี": acc.name,
                    "ค่า Ads FB (฿)": acc_ads,
                    "คอมมิชชัน (฿)": acc_comm,
                    "กำไร/ขาดทุน (฿)": acc_profit
                })
                
                # เก็บข้อมูล transaction ไว้ทำกราฟและโหลด Excel
                for t in acc.transactions:
                    transaction_data.append({
                        "วันที่": t.created_at.strftime("%Y-%m-%d"),
                        "บัญชี": acc.name,
                        "ร้านค้า": t.shop_name,
                        "ชื่อสินค้า": t.product_name,
                        "คอมมิชชัน": t.commission_amount
                    })

            net_profit = total_comm - total_ads

            # 1. โชว์สถิติภาพรวม (Macro)
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 คอมมิชชันรวมทั้งหมด", f"฿ {total_comm:,.2f}")
            col2.metric("💸 ค่า Ads รวม", f"฿ {total_ads:,.2f}")
            col3.metric("🎯 กำไรสุทธิ (หลังหัก Ads)", f"฿ {net_profit:,.2f}", delta=float(net_profit))

            st.markdown("---")

            # 2. ตารางรายบัญชีพร้อมสีเขียว-แดง
            st.subheader("📋 รายละเอียดกำไร-ขาดทุน (รายบัญชี)")
            df_acc = pd.DataFrame(acc_data)
            
            def color_profit(val):
                color = '#10b981' if val > 0 else '#ef4444' if val < 0 else 'gray'
                return f'color: {color}; font-weight: bold;'
            
            st.dataframe(df_acc.style.map(color_profit, subset=['กำไร/ขาดทุน (฿)']), use_container_width=True)
            
            st.markdown("---")
            
            # 3. กราฟและโหลดไฟล์
            if transaction_data:
                df_trans = pd.DataFrame(transaction_data)
                
                col_chart, col_dl = st.columns([3, 1])
                with col_chart:
                    st.markdown("**📈 ยอดคอมมิชชันแยกตามร้านค้า**")
                    shop_summary = df_trans.groupby('ร้านค้า')['คอมมิชชัน'].sum().reset_index()
                    st.bar_chart(shop_summary.set_index('ร้านค้า'))
                
                with col_dl:
                    st.markdown("**📥 ดาวน์โหลดข้อมูลยอดขาย**")
                    csv = df_trans.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("โหลดไฟล์ Excel (CSV)", data=csv, file_name='affiliate_data.csv', mime='text/csv')
        else:
            st.info("ยังไม่มีข้อมูลบัญชี กรุณาไปที่เมนู 'จัดการบัญชี' เพื่อเริ่มใช้งานครับ")

    # ------------------------------------------
    # เมนูที่ 2: จัดการบัญชี (เพิ่มค่า Ads)
    # ------------------------------------------
    elif menu == "💼 จัดการบัญชี (เพิ่มค่า Ads)":
        st.title("💼 จัดการบัญชี Affiliate")
        with st.form("add_account_form"):
            st.subheader("➕ เพิ่มบัญชีใหม่")
            acc_name = st.text_input("ชื่อบัญชี (เช่น TikTok-หลัก, FB-เพจสำรอง)")
            ads_cost = st.number_input("💸 ค่า Ads FB สำหรับบัญชีนี้ (บาท)", min_value=0.0, step=100.0)
            
            if st.form_submit_button("บันทึกบัญชี"):
                if acc_name:
                    new_acc = AffiliateAccount(name=acc_name, fb_ads_cost=ads_cost, owner_id=current_user.id)
                    session.add(new_acc)
                    session.commit()
                    st.success(f"เพิ่มบัญชี {acc_name} พร้อมค่าโฆษณา {ads_cost} บาท เรียบร้อยแล้ว!")
                    st.rerun()
                else:
                    st.error("กรุณากรอกชื่อบัญชีครับ")
        
        st.markdown("---")
        st.subheader("📋 บัญชีของคุณทั้งหมด")
        accounts = session.query(AffiliateAccount).filter_by(owner_id=current_user.id).all()
        if accounts:
            for acc in accounts:
                st.write(f"- **{acc.name}** (ต้นทุน Ads: ฿{acc.fb_ads_cost:,.2f})")
        else:
            st.write("ยังไม่มีบัญชี")

    # ------------------------------------------
    # เมนูที่ 3: บันทึกยอดขาย
    # ------------------------------------------
    elif menu == "📝 บันทึกยอดขาย":
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
                commission = st.number_input("ยอดคอมมิชชันที่ได้ (บาท)", min_value=0.0, step=1.0)
                
                if st.form_submit_button("บันทึกยอด"):
                    if order_id and product_name:
                        new_trans = TransactionRecord(
                            order_id=order_id,
                            account_id=acc_dict[selected_acc],
                            product_name=product_name,
                            shop_name=shop_name,
                            commission_amount=commission
                        )
                        session.add(new_trans)
                        session.commit()
                        st.success("✅ บันทึกยอดสำเร็จ!")
                    else:
                        st.error("กรุณากรอกรหัสคำสั่งซื้อและชื่อสินค้าครับ")
