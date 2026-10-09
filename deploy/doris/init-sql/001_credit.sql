-- DataPlat 本地测试数据初始化（Doris）
-- 由 Doris 镜像的 /docker-entrypoint-initdb.d 机制执行（BE 首次启动后自动灌入）
-- 业务库：credit（信贷领域测试库）
-- 说明：Doris 2.0 使用 MySQL 协议；Unique Key 表用于可更新事实，Aggregate 表用于指标汇总

CREATE DATABASE IF NOT EXISTS credit;
USE credit;

-- 1) 客户维度表
CREATE TABLE IF NOT EXISTS customer (
    customer_id      BIGINT         COMMENT '客户编号',
    customer_name    VARCHAR(64)    COMMENT '客户姓名',
    gender           VARCHAR(8)     COMMENT '性别',
    birth_date       DATEV2           COMMENT '出生日期',
    id_card          VARCHAR(32)    COMMENT '证件号',
    phone            VARCHAR(32)    COMMENT '手机号',
    email            VARCHAR(128)   COMMENT '邮箱',
    address          VARCHAR(256)   COMMENT '地址',
    credit_score     INT            COMMENT '征信分',
    customer_status  VARCHAR(16)    COMMENT '客户状态',
    create_time      DATETIME       COMMENT '创建时间',
    update_time      DATETIME       COMMENT '更新时间'
)
UNIQUE KEY (customer_id)
DISTRIBUTED BY HASH (customer_id) BUCKETS 8
PROPERTIES (
    "replication_num" = "2",
    "storage_medium" = "HDD"
);

-- 2) 账户维度表
CREATE TABLE IF NOT EXISTS account (
    account_id       BIGINT         COMMENT '账户编号',
    customer_id      BIGINT         COMMENT '客户编号',
    account_type     VARCHAR(16)    COMMENT '账户类型',
    open_date        DATEV2           COMMENT '开户日期',
    status           VARCHAR(16)    COMMENT '账户状态',
    balance          DECIMAL(20,2)  COMMENT '账户余额',
    currency         VARCHAR(8)     COMMENT '币种',
    create_time      DATETIME       COMMENT '创建时间',
    update_time      DATETIME       COMMENT '更新时间'
)
UNIQUE KEY (account_id)
DISTRIBUTED BY HASH (account_id) BUCKETS 8
PROPERTIES (
    "replication_num" = "2",
    "storage_medium" = "HDD"
);

-- 3) 贷款合同事实表
CREATE TABLE IF NOT EXISTS loan_contract (
    contract_no      VARCHAR(32)    COMMENT '合同编号',
    customer_id      BIGINT         COMMENT '客户编号',
    product_code     VARCHAR(16)    COMMENT '产品代码',
    product_name     VARCHAR(64)    COMMENT '产品名称',
    currency         VARCHAR(8)     COMMENT '币种',
    loan_amount      DECIMAL(20,2)  COMMENT '贷款金额',
    loan_balance     DECIMAL(20,2)  COMMENT '贷款余额',
    annual_rate      DECIMAL(10,4)  COMMENT '年利率',
    term_months      INT            COMMENT '期限（月）',
    repay_method     VARCHAR(32)    COMMENT '还款方式',
    begin_date       DATEV2           COMMENT '放款日期',
    end_date         DATEV2           COMMENT '到期日期',
    overdue_days     INT            COMMENT '逾期天数',
    status           VARCHAR(16)    COMMENT '合同状态',
    create_time      DATETIME       COMMENT '创建时间',
    update_time      DATETIME       COMMENT '更新时间'
)
UNIQUE KEY (contract_no)
DISTRIBUTED BY HASH (contract_no) BUCKETS 8
PROPERTIES (
    "replication_num" = "2",
    "storage_medium" = "HDD"
);

-- 4) 还款流水事实表
CREATE TABLE IF NOT EXISTS repay_record (
    repay_id         BIGINT         COMMENT '流水ID',
    contract_no      VARCHAR(32)    COMMENT '合同编号',
    repay_date       DATEV2           COMMENT '还款日期',
    repay_principal  DECIMAL(20,2)  COMMENT '还本金',
    repay_interest   DECIMAL(20,2)  COMMENT '还利息',
    repay_amount     DECIMAL(20,2)  COMMENT '还款总额',
    channel          VARCHAR(16)    COMMENT '还款渠道',
    create_time      DATETIME       COMMENT '创建时间'
)
UNIQUE KEY (repay_id)
DISTRIBUTED BY HASH (repay_id) BUCKETS 8
PROPERTIES (
    "replication_num" = "2",
    "storage_medium" = "HDD"
);

-- 5) 逾期事实表
CREATE TABLE IF NOT EXISTS overdue_record (
    overdue_id       BIGINT         COMMENT '逾期ID',
    contract_no      VARCHAR(32)    COMMENT '合同编号',
    overdue_days     INT            COMMENT '逾期天数',
    overdue_principal DECIMAL(20,2) COMMENT '逾期本金',
    overdue_interest DECIMAL(20,2)  COMMENT '逾期利息',
    risk_level       VARCHAR(16)    COMMENT '风险等级',
    begin_date       DATEV2           COMMENT '逾期开始日期',
    end_date         DATEV2           COMMENT '逾期结束日期',
    status           VARCHAR(16)    COMMENT '状态',
    create_time      DATETIME       COMMENT '创建时间'
)
UNIQUE KEY (overdue_id)
DISTRIBUTED BY HASH (overdue_id) BUCKETS 8
PROPERTIES (
    "replication_num" = "2",
    "storage_medium" = "HDD"
);

-- 6) 汇总指标（聚合模型）
CREATE TABLE IF NOT EXISTS loan_summary_daily (
    stat_date        DATEV2           COMMENT '统计日期',
    product_code     VARCHAR(16)    COMMENT '产品代码',
    loan_count       BIGINT         SUM  COMMENT '贷款笔数',
    loan_amount      DECIMAL(20,2)  SUM  COMMENT '贷款总额',
    overdue_count    BIGINT         SUM  COMMENT '逾期笔数',
    overdue_amount   DECIMAL(20,2)  SUM  COMMENT '逾期总额'
)
AGGREGATE KEY (stat_date, product_code)
DISTRIBUTED BY HASH (stat_date, product_code) BUCKETS 8
PROPERTIES (
    "replication_num" = "2",
    "storage_medium" = "HDD"
);
-- ============ 演示数据 ============

INSERT INTO customer (customer_id, customer_name, gender, birth_date, id_card, phone, email, address, credit_score, customer_status, create_time, update_time) VALUES
(1001, '张伟',   'M', '1985-06-12', '110101198506120011', '13800138001', 'zhangwei@example.com',   '北京市朝阳区', 780, 'ACTIVE',  '2024-01-05 09:30:00', '2024-06-20 10:00:00'),
(1002, '李娜',   'F', '1990-03-08', '110101199003080022', '13800138002', 'lina@example.com',       '上海市浦东新区', 720, 'ACTIVE',  '2024-02-12 11:20:00', '2024-06-22 09:10:00'),
(1003, '王强',   'M', '1978-11-20', '110101197811200033', '13800138003', 'wangqiang@example.com', '广州市天河区', 650, 'ACTIVE',  '2024-03-01 08:45:00', '2024-06-25 14:30:00'),
(1004, '赵敏',   'F', '1995-09-15', '110101199509150044', '13800138004', 'zhaomin@example.com',   '深圳市南山区', 810, 'ACTIVE',  '2024-04-18 16:05:00', '2024-07-01 10:40:00'),
(1005, '刘洋',   'M', '1982-01-25', '110101198201250055', '13800138005', 'liuyang@example.com',   '成都市高新区', 590, 'ACTIVE',  '2024-05-22 10:50:00', '2024-07-05 15:20:00'),
(1006, '陈静',   'F', '1988-07-30', '110101198807300066', '13800138006', 'chenjing@example.com',  '杭州市西湖区', 700, 'ACTIVE',  '2024-06-11 13:25:00', '2024-07-08 09:00:00');

INSERT INTO account (account_id, customer_id, account_type, open_date, status, balance, currency, create_time, update_time) VALUES
(20001, 1001, 'SAVINGS',  '2024-01-05', 'ACTIVE',   51230.50, 'CNY', '2024-01-05 09:30:00', '2024-07-10 08:00:00'),
(20002, 1002, 'SAVINGS',  '2024-02-12', 'ACTIVE',   20500.00, 'CNY', '2024-02-12 11:20:00', '2024-07-10 08:00:00'),
(20003, 1003, 'CURRENT',  '2024-03-01', 'ACTIVE',    8120.75, 'CNY', '2024-03-01 08:45:00', '2024-07-10 08:00:00'),
(20004, 1004, 'SAVINGS',  '2024-04-18', 'ACTIVE',  158000.00, 'CNY', '2024-04-18 16:05:00', '2024-07-10 08:00:00'),
(20005, 1005, 'CURRENT',  '2024-05-22', 'ACTIVE',    3500.00, 'CNY', '2024-05-22 10:50:00', '2024-07-10 08:00:00'),
(20006, 1006, 'SAVINGS',  '2024-06-11', 'ACTIVE',   78900.20, 'CNY', '2024-06-11 13:25:00', '2024-07-10 08:00:00');

INSERT INTO loan_contract (contract_no, customer_id, product_code, product_name, currency, loan_amount, loan_balance, annual_rate, term_months, repay_method, begin_date, end_date, overdue_days, status, create_time, update_time) VALUES
('L202400001', 1001, 'P001', '个人消费贷', 'CNY', 100000.00,  68000.00, 0.0450, 24, 'EQUAL_PRINCIPAL',  '2024-02-01', '2026-02-01', 0,  'NORMAL',  '2024-02-01 10:00:00', '2024-07-01 09:00:00'),
('L202400002', 1002, 'P002', '个人住房贷', 'CNY', 800000.00, 750000.00, 0.0420, 360, 'EQUAL_INSTALLMENT', '2024-03-15', '2054-03-15', 0,  'NORMAL',  '2024-03-15 09:30:00', '2024-07-01 09:00:00'),
('L202400003', 1003, 'P003', '小微企业贷', 'CNY', 500000.00, 320000.00, 0.0550, 36, 'EQUAL_INSTALLMENT', '2024-04-01', '2027-04-01', 12, 'OVERDUE',  '2024-04-01 14:00:00', '2024-07-01 09:00:00'),
('L202400004', 1004, 'P001', '个人消费贷', 'CNY',  50000.00,  25000.00, 0.0480, 12, 'EQUAL_PRINCIPAL',  '2024-05-10', '2025-05-10', 0,  'NORMAL',  '2024-05-10 08:30:00', '2024-07-01 09:00:00'),
('L202400005', 1005, 'P004', '个人经营贷', 'CNY', 300000.00, 300000.00, 0.0600, 60, 'EQUAL_INSTALLMENT', '2024-06-20', '2029-06-20', 35, 'OVERDUE',  '2024-06-20 11:00:00', '2024-07-01 09:00:00'),
('L202400006', 1006, 'P002', '个人住房贷', 'CNY', 600000.00, 600000.00, 0.0390, 240, 'EQUAL_INSTALLMENT', '2024-07-05', '2044-07-05', 0,  'NORMAL',  '2024-07-05 10:15:00', '2024-07-05 10:15:00');

INSERT INTO repay_record (repay_id, contract_no, repay_date, repay_principal, repay_interest, repay_amount, channel, create_time) VALUES
(30001, 'L202400001', '2024-03-01',  4000.00,  375.00,  4375.00, 'APP',   '2024-03-01 08:00:00'),
(30002, 'L202400001', '2024-04-01',  4000.00,  350.00,  4350.00, 'APP',   '2024-04-01 08:00:00'),
(30003, 'L202400001', '2024-05-01',  4000.00,  325.00,  4325.00, 'BANK',  '2024-05-01 08:00:00'),
(30004, 'L202400001', '2024-06-01',  4000.00,  300.00,  4300.00, 'BANK',  '2024-06-01 08:00:00'),
(30005, 'L202400001', '2024-07-01',  4000.00,  275.00,  4275.00, 'APP',   '2024-07-01 08:00:00'),
(30006, 'L202400002', '2024-04-15',  2500.00, 2800.00,  5300.00, 'APP',   '2024-04-15 08:00:00'),
(30007, 'L202400002', '2024-05-15',  2500.00, 2750.00,  5250.00, 'BANK',  '2024-05-15 08:00:00'),
(30008, 'L202400002', '2024-06-15',  2500.00, 2700.00,  5200.00, 'BANK',  '2024-06-15 08:00:00'),
(30009, 'L202400002', '2024-07-15',  2500.00, 2650.00,  5150.00, 'APP',   '2024-07-15 08:00:00'),
(30010, 'L202400003', '2024-05-01',  5000.00, 2100.00,  7100.00, 'APP',   '2024-05-01 08:00:00'),
(30011, 'L202400003', '2024-06-01',  5000.00, 2000.00,  7000.00, 'APP',   '2024-06-01 08:00:00'),
(30012, 'L202400004', '2024-06-10',  5000.00,  200.00,  5200.00, 'APP',   '2024-06-10 08:00:00'),
(30013, 'L202400004', '2024-07-10',  5000.00,  180.00,  5180.00, 'BANK',  '2024-07-10 08:00:00');

INSERT INTO overdue_record (overdue_id, contract_no, overdue_days, overdue_principal, overdue_interest, risk_level, begin_date, end_date, status, create_time) VALUES
(40001, 'L202400003', 12, 21000.00, 420.00, 'C', '2024-06-20', '2024-07-02', 'SETTLED', '2024-06-21 09:00:00'),
(40002, 'L202400005', 35, 30000.00, 900.00, 'B', '2024-06-25', NULL,         'ACTIVE',  '2024-06-26 09:00:00');

INSERT INTO loan_summary_daily (stat_date, product_code, loan_count, loan_amount, overdue_count, overdue_amount) VALUES
('2024-07-01', 'P001', 2, 150000.00, 0,      0.00),
('2024-07-01', 'P002', 2, 1400000.00, 0,     0.00),
('2024-07-01', 'P003', 1, 500000.00,  1,     21000.00),
('2024-07-01', 'P004', 1, 300000.00,  1,     30000.00);

-- ============ 演示查询 ============
-- 1) 贷款合同按状态分布
-- SELECT status, COUNT(*) AS cnt, SUM(loan_amount) AS amt FROM credit.loan_contract GROUP BY status;
-- 2) 逾期客户 TOP
-- SELECT c.customer_name, l.contract_no, l.overdue_days, l.loan_balance
-- FROM credit.loan_contract l JOIN credit.customer c ON l.customer_id=c.customer_id
-- WHERE l.status='OVERDUE' ORDER BY l.overdue_days DESC;
