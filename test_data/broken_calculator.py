"""
Broken Calculator - Has multiple syntax and compilation errors
This should trigger the compilation_fixer_tool
"""

class Calculator
    """Calculator with syntax errors"""
    
    def __init__(self):
        self.result = 0
    
    def add(self, x, y)
        # Missing colon
        return x + y
    
    def subtract(self, x, y):
        # Undefined variable
        return a - b
    
    def multiply(self, x, y):
        # Wrong indentation
      return x * y
    
    def divide(self, x, y):
        # Missing return statement
        result = x / y
    
    def power(self, x, y):
        # Using undefined function
        return pow_function(x, y)

# Missing main guard
calculator = Calculator()
print(calculator.add(5, 3))
print(calculator.subtract(10 4))  # Missing comma
print(calculator.multiply(2, 3)
print(calculator.divide(10, 2))
