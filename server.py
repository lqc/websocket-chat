import uuid
from redis import StrictRedis as RedisConnection 

from gevent import monkey, pywsgi, spawn
from geventwebsocket.handler import WebSocketHandler 

monkey.patch_all()


def channel_listener(websocket, room_name, client_id):
    conn = RedisConnection()
    pubsub = conn.pubsub()
    pubsub.psubscribe("%s.*" % room_name)
    
    me = "%s.%s" % (room_name, client_id)
    try:
        for msg in pubsub.listen():
            if websocket.socket is None:
                return
            if msg["channel"] == me:
                continue 
            websocket.send("%s: %s" % (msg["channel"], msg["data"]))
    finally:
        pubsub.punsubscribe("%s.*" % room_name)
 
def serve_chat(websocket, room_name):
    client_uuid = uuid.uuid4()
        
    # subscribe the client to channel
    spawn(channel_listener, websocket, room_name, client_uuid)
    
    conn = RedisConnection()
    
    try:
        while True:
            # message from client
            message = websocket.receive()
            if message is None:
                return
            conn.publish("%s.%s" % (room_name, client_uuid), message)      
    finally:
        websocket.close()
        

def index(env, start_response):
    if env['PATH_INFO'] == '/':
        start_response('200 OK', [('Content-Type', 'text/html')])
        return open("index.html", "rb")
    print env["PATH_INFO"]
    if "wsgi.websocket" not in env:
        start_response('404 Not Found', [('Content-Type', 'text/html')])
        return ['<html><body><p>Websocket is required</p></body></html>']
    else:
        # we have a websocket, spawn a new greenlet 
        serve_chat(env["wsgi.websocket"], env['PATH_INFO'][1:])
    

server = pywsgi.WSGIServer(('0.0.0.0', 8000), index, handler_class=WebSocketHandler)
print "Serving..."
server.serve_forever()