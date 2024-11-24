# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution:
    def detectCycle(self, head: Optional[ListNode]) -> Optional[ListNode]:
        check = set()  # Use a set for efficient lookup
        cur = head
        while cur:
            if cur in check:
                return cur
            check.add(cur)
            cur = cur.next  # Move to the next node
        return None  # No cycle found