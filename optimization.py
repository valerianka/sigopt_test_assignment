# Use SigOpt to find the maximum value of this function
# Normally we would optimie a real machine learning model here and try to 
# increase its accuracy. However, setting up ML in your Ubuntu environment
# requires a large amount of setup that we would like to skip for the
# sake of brevity in this exercise.
def optimize(channel):
    import math
    import time

    channel.send("ready")
    for tup in channel:
        if tup is None:  # we can shutdown
            break
        # sleep 2 seconds to imitate long calculating time, send result
        suggestion_id = tup[0]
        x = tup[1]
        y = tup[2]        
        time.sleep(2) # this line can be deleted
        result = (.75 * math.exp(-(9 * x - 2) ** 2 / 4.0 - (9 * y - 2) ** 2 / 4.0) +
             .75 * math.exp(-(9 * x + 1) ** 2 / 49.0 - (9 * y + 1) / 10.0) +
             .5 * math.exp(-(9 * x - 7) ** 2 / 4.0 - (9 * y - 3) ** 2 / 4.0) -
             .2 * math.exp(-(9 * x - 4) ** 2 - (9 * y - 7) ** 2))
        channel.send((suggestion_id, result))  
