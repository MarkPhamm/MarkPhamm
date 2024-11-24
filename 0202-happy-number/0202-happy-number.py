class Solution:
    def isHappy(self, n: int) -> bool:
        def digitsum(n):
            sum = 0 
            list_n = list(str(n))
            for num in list_n:
                sum+= int(num)**2
            return sum
        
        while True:
            if n < 10:
                if n == 1 or n == 7:
                    return True
            if n**2 == digitsum(n):
                return False 
            if digitsum(n) == 1:
                return True
            n = digitsum(n)