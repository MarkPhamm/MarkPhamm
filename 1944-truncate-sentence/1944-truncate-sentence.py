class Solution:
    def truncateSentence(self, s: str, k: int) -> str:
        str_list = s.split()
        return ' '.join(str_list[:k])