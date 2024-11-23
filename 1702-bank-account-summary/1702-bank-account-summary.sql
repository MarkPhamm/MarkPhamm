# Write your MySQL query statement below
WITH total_transacts AS
(
SELECT user_id, SUM(transact) total_transact FROM 
(
SELECT  paid_by user_id, -amount as transact FROM Transactions
UNION ALL
SELECT  paid_to user_id, amount as transact FROM Transactions
) a
GROUP BY 1 
)

SELECT user_id, user_name,
credit + ifnull(total_transact,0) credit,
IF(credit + ifnull(total_transact,0)<0, "Yes","No") credit_limit_breached
FROM Users
LEFT JOIN total_transacts 
USING(user_id)