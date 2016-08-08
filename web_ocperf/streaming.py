from tornado import gen

@gen.coroutine
def update(line, source):
    s = line.split(',')

    timestamp = None
    value = None
    event = None

    print("[UPDATE] Source ID: " + str(id(source)))

    try:
        timestamp = float(s[0])
    except:
        print "Problem with timestamp: " + s[0]

    try:
        event = s[3]
    except:
        print "Problem with event name: " + s[3]

    try:
        value = int(s[1])
    except:
        value = 0
        print "problem with value parsing: " + s[1]

    print("doing update")
    print(timestamp, value, event)
    source.stream(dict(x=[timestamp], y=[value]))

def session_task(session):
    print("Spawning background session task")
    session.loop_until_closed()
    print("closed!")
