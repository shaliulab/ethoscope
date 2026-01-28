from ethoscope.stimulators.pwm_stimulator import merge_asof



d = {"time": [0, 10, 20], "pwm": [1,2,3]}


result = merge_asof(d, 15)
assert result["pwm"][0]==2

result = merge_asof(d, 5)
assert result["pwm"][0]==1

result = merge_asof(d, 30)
assert result["pwm"][0]==3

result = merge_asof(d, 0)
assert result["pwm"][0]==1
