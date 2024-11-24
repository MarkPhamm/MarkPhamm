class Solution:
    def sortTheStudents(self, score: List[List[int]], k: int) -> List[List[int]]:
        array = []
        for s in score:
            array.append([s[k],s])
        array.sort(reverse=True)
        
        ans = []
        for a in array:
            ans.append(a[1])
        return ans
        