def multiply(a: int, b: int) -> int:
    """Multiply two integers and return their product."""
    # @tool 将函数包装成工具对象；invoke 传入参数字典后才执行这行。
    return a + b
call = {"args": {"a": 37, "b": 58}}
print(multiply(**call["args"]))
#print(multiply(call["args"]))