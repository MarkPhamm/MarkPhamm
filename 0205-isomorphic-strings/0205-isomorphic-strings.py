class Solution:
    def isIsomorphic(self, s: str, t: str) -> bool:
        if len(s) != len(t):
            return False
        lookup_st = {}
        lookup_ts = {}
        
        for i in range(len(s)):
            if s[i] not in lookup_st:
                lookup_st[s[i]] = {t[i]}
            else:
                lookup_st[s[i]].add(t[i])
        
        for i in range(len(s)):
            if t[i] not in lookup_ts:
                lookup_ts[t[i]] = {s[i]}
            else:
                lookup_ts[t[i]].add(s[i])

        for val in lookup_st.values():
            if len(val) == 2:
                return False

        for val in lookup_ts.values():
            if len(val) == 2:
                return False
        
        return True
        

        