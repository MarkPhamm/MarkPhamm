# Write your MySQL query statement below
SELECT distinct num ConsecutiveNums FROM
(
SELECT 
    id,
    num,
    id - ROW_NUMBER() OVER(partition by num ORDER BY id) group_id
FROM Logs
) a
GROUP BY num, group_id
HAVING COUNT(*) >= 3


