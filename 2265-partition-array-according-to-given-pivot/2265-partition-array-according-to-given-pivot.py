class Solution:
    def pivotArray(self, nums: List[int], pivot: int) -> List[int]:
        smaller = []
        equal = []
        larger = []
        for num in nums:
            if num == pivot:
                equal.append(num)
            elif num < pivot:
                smaller.append(num)
            else:
                larger.append(num)
        
        return smaller + equal + larger
        