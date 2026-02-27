import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
import enum
import random

Base = declarative_base()

class PlatformEnum(enum.Enum):
    SHOPEE = "shopee"
    TIKTOK = "tiktok"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class AffiliateAccount(Base):
    __tablename__ = 'affiliate_accounts'
    id = Column(Integer, primary_key=True)
    account_name = Column(String(100), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    affiliate_id = Column(String(100), unique=True, nullable=False)
    transactions = relationship("TransactionRecord", back_populates="account")

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

engine = create_engine('sqlite:///affiliate_farm.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# ข้อมูลจำลองร้านค้าและสินค้า
DUMMY_SHOPS = ["GadgetZ", "HomeDecor Hub", "Beauty Store", "Fashion BKK"]
DUMMY_PRODUCTS = ["หูฟังบลูทูธ 5.0", "พาวเวอร์แบงค์ 20000mAh", "กล่องเก็บของมินิมอล", "โคมไฟตั้งโต๊ะ LED", "เซรั่มวิตามินซี", "เสื้อยืดโอเวอร์ไซส์"]

def seed_dummy_data():
    if session.query(AffiliateAccount).count() == 0:
        acc1 = AffiliateAccount(account_name="Shopee_Main_01", platform=PlatformEnum.SHOPEE, affiliate_id="SHP001")
        acc2 = AffiliateAccount(account_name="Shopee_Sub_02", platform=PlatformEnum.SHOPEE, affiliate_id="SHP002")
        session.add_all([acc1, acc2])
        session.commit()

        # สุ่มสร้างออเดอร์พร้อมระบุชื่อสินค้าและร้านค้า
        for i in range(80):
            txn = TransactionRecord(
                order_id=f"ORD1_{i}", 
                account_id=acc1.id, 
                product_name=random.choice(DUMMY_PRODUCTS),
                shop_name=random.choice(DUMMY_SHOPS),
                commission_amount=random.uniform(5.0, 20.0), 
                status=OrderStatus.APPROVED
            )
            session.add(txn)
            
        for i in range(100):
            txn = TransactionRecord(
                order_id=f"ORD2_{i}", 
                account_id=acc2.id, 
                product_name=random.choice(DUMMY_PRODUCTS),
                shop_name=random.choice(DUMMY_SHOPS),
                commission_amount=random.uniform(5.0, 25.0), 
                status=OrderStatus.APPROVED
            )
            session.add(txn)
        session.commit()

seed_dummy_data()

# ==========================
# ส่วนของหน้า Dashboard (UI)
# ==========================
st.set_page_config(page_title="Affiliate Farm Dashboard", layout="wide")

# 1. สร้าง Sidebar เมนูด้านซ้ายมือสำหรับ Filter เลือกบัญชี
st.sidebar.header("⚙️ ตัวกรองข้อมูล (Filter)")
all_accounts = session.query(AffiliateAccount.account_name).all()
account_list = ["ดูทุกบัญชีรวมกัน"] + [acc[0] for acc in all_accounts]
selected_account = st.sidebar.selectbox("🔍 เลือกบัญชีที่ต้องการดู:", account_list)

st.title("📊 Affiliate Farm Dashboard")
st.markdown(f"**กำลังแสดงข้อมูลสำหรับ:** `{selected_account}`")
st.divider()

TARGET_COMMISSION = 500.0
TARGET_ORDERS = 90

# สร้าง Query สรุปยอดรวม (ดึงตามบัญชีที่เลือก)
summary_query = session.query(
    AffiliateAccount.account_name,
    func.sum(TransactionRecord.commission_amount).label('total_commission'),
    func.count(TransactionRecord.id).label('total_orders')
).outerjoin(TransactionRecord)

if selected_account != "ดูทุกบัญชีรวมกัน":
    summary_query = summary_query.filter(AffiliateAccount.account_name == selected_account)

results = summary_query.group_by(AffiliateAccount.id).all()

# 2. แสดงผลหลอด Progress Bar
for row in results:
    acc_name = row.account_name
    comm = row.total_commission or 0.0
    orders = row.total_orders or 0
    
    st.subheader(f"🛒 สรุปเป้าหมายบัญชี: {acc_name}")
    col1, col2 = st.columns(2)
    
    with col1:
        comm_percent = min(comm / TARGET_COMMISSION, 1.0)
        if comm >= TARGET_COMMISSION:
            st.metric(label="ยอดคอมมิชชั่นสะสม (บาท)", value=f"฿{comm:,.2f}", delta="🎉 ทะลุเป้าหมายแล้ว!")
        else:
            st.metric(label="ยอดคอมมิชชั่นสะสม (บาท)", value=f"฿{comm:,.2f}", delta=f"- ฿{TARGET_COMMISSION - comm:,.2f} (ขาดอีก)", delta_color="inverse")
        st.progress(comm_percent)

    with col2:
        order_percent = min(orders / TARGET_ORDERS, 1.0)
        if orders >= TARGET_ORDERS:
            st.metric(label="จำนวนออเดอร์สะสม", value=f"{orders} ออเดอร์", delta="🎉 ทะลุเป้าหมายแล้ว!")
        else:
            st.metric(label="จำนวนออเดอร์สะสม", value=f"{orders} ออเดอร์", delta=f"- {TARGET_ORDERS - orders} ออเดอร์ (ขาดอีก)", delta_color="inverse")
        st.progress(order_percent)
        
    st.markdown("<br>", unsafe_allow_html=True) # เว้นบรรทัดนิดนึง

st.divider()

# 3. ตารางจัดอันดับสินค้า/ร้านค้าขายดี (Ranking)
st.subheader("🏆 จัดอันดับสินค้าและร้านค้าทำเงิน (Top Performers)")
st.markdown("ข้อมูลสินค้าที่สร้างค่าคอมมิชชั่นให้คุณมากที่สุด เอาไปใช้ทำคอนเทนต์ต่อได้เลย!")

# Query ข้อมูลเพื่อจัดอันดับ
rank_query = session.query(
    TransactionRecord.shop_name.label('ร้านค้า (Shop)'),
    TransactionRecord.product_name.label('ชื่อสินค้า (Product)'),
    func.count(TransactionRecord.id).label('จำนวนออเดอร์'),
    func.sum(TransactionRecord.commission_amount).label('ค่าคอมมิชชั่นรวม (บาท)')
).join(AffiliateAccount)

# กรองข้อมูลตารางตามที่เลือกใน Sidebar
if selected_account != "ดูทุกบัญชีรวมกัน":
    rank_query = rank_query.filter(AffiliateAccount.account_name == selected_account)

# จัดกลุ่มตามร้านและสินค้า เรียงตามค่าคอมจากมากไปน้อย (desc)
top_performers = rank_query.group_by(TransactionRecord.shop_name, TransactionRecord.product_name) \
                           .order_by(func.sum(TransactionRecord.commission_amount).desc()) \
                           .all()

# นำข้อมูลมาแสดงเป็นตารางสวยๆ
if top_performers:
    df_ranking = pd.DataFrame(top_performers)
    # จัด Format ให้ดูเป็นเงินบาทสวยๆ
    df_ranking['ค่าคอมมิชชั่นรวม (บาท)'] = df_ranking['ค่าคอมมิชชั่นรวม (บาท)'].apply(lambda x: f"฿{x:,.2f}")
    
    # แสดงตารางแบบเต็มจอ
    st.dataframe(df_ranking, use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มีข้อมูลการขายสำหรับบัญชีนี้ครับ")
