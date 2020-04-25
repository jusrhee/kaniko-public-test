import pelletenv as pe
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import logging
from engineio.payload import Payload

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
Payload.max_decode_packets = 100

app = Flask(__name__)
socketio = SocketIO(app)
env = pe.StaticPelletEnv()

def parseState(env):
  players = env.playerDict.copy()
  bullets = env.bulletList.copy()
  
  for p in players:
    players[p] = {
      'x': players[p].x,
      'y': players[p].y,
      'vx': players[p].vx,
      'vy': players[p].vy,
      'lives': players[p].lives,
      'isHuman': players[p].isHuman,
      'grid': players[p].fov.grid.tolist()
    }
  
  for b in range(len(bullets)):
    bullets[b] = {
      'x': bullets[b].x,
      'y': bullets[b].y
    }

  return {
    'players': players,
    'bullets': bullets,
    'scores': env.scores
  }

@app.route('/')
def hello_world():
    return parseState(env)
    
@socketio.on('connect')
def test_connect():
  print('Socket connected')
  emit('confirm', pe.conf)

@socketio.on('reset')
def on_reset():
  env.reset()
  emit('update', parseState(env))

@socketio.on('step')
def on_step(action):
  env.step({ 0: action })
  emit('update', parseState(env))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)