import numpy as np
pygame = None

# Object to enable portability
# TODO: Relocate to environment (for different modes?)
conf = {
  'SPACE_WIDTH': 500,
  'SPACE_HEIGHT': 500,
  'PLAYER_RADIUS': 30,
  'BULLET_RADIUS': 10,
  'INPUT_FORCE': 1,
  'FRICTION_FORCE': 0.6,
  'PLAYER_MAX_VEL': 10,
  'BULLET_VEL': 15,
  'FIRE_COOLDOWN': 20,
  'VEL_KILL_EPSILON': 0.3,
  'WALL_WIDTH': 10,
  'NUM_LIVES': 3,
  'FOV_DISTANCE': 250,
  'GRID_RADIUS': 5,
}

defaultConf = conf.copy()

class PelletEnv():
  def __init__(self):

    # Repeated outside reset() so the syntax highlighter doesn't freak out
    self.scores = {}
    self.alive = {}
    self.actionLog = None
    self.playerCount = 0
    self.t = 0
    self.done = False
    self.observations = {}
    self.playerDict = {}

    # Must be a list (not set) to support size change during iteration
    self.bulletList = []

    self.reset()

  # Helper for adding a player mid-run (returns player ID)
  def addPlayer(self, x=None, y=None, isHuman=False):
    if (x is None or y is None):
      d = conf['SPACE_WIDTH'] - (2 * conf['WALL_WIDTH']) - (2 * conf['PLAYER_RADIUS'])
      x = np.random.rand() * d
      y = np.random.rand() * d

    player = Player(x, y, self, self.playerCount, isHuman)
    self.playerDict[self.playerCount] = player
    self.scores[self.playerCount] = 0
    self.alive[self.playerCount] = 1
    self.observations[self.playerCount] = self.getPlayerObs(player)

    self.playerCount += 1
    return self.playerCount - 1

  def step(self, actions):
    self.actionLog = actions
    self.t += 1

    for id in self.playerDict:
      if (id in actions):
        self.playerDict[id].update(actions[id])

    for i in range(len(self.bulletList)):

      # Need this check since list size can update while iterating
      if i < len(self.bulletList):
        bullet = self.bulletList[i]
        bullet.update()

    # Not consolidated with agent update loop to prevent information asymmetry
    for id in self.playerDict:
      player = self.playerDict[id]
      player.updateFOV()
      self.observations[id] = self.getPlayerObs(player)

    if self.t > 2:
      self.done = True

    return {
      'observation': self.observations,
      'rewards': self.getRew(),
      'done': self.done
    }

  # Outside Player to allow for global observation
  def getPlayerObs(self, player):
    obs = player.fov.grid.flatten()
    obs = np.concatenate((obs, [player.vx], [player.vy]), axis=0)
    return obs

  def getRew(self):
    return self.scores

  def reset(self):
    conf = defaultConf

    self.scores = {}
    self.alive = {}
    self.actionLog = None
    self.playerCount = 0
    self.t = 0
    self.done = False
    self.observations = {}
    self.playerDict = {}
    self.bulletList = []

    self.addPlayer(100, conf['SPACE_HEIGHT'] // 2, True)
    self.addPlayer(conf['SPACE_WIDTH'] - 100, conf['SPACE_HEIGHT'] // 2, False)

    return self.observations

  # Vanilla reset that adds no players
  def emptyReset(self):
    self.scores = {}
    self.alive = {}
    self.actionLog = None
    self.playerCount = 0
    self.t = 0
    self.done = False
    self.observations = {}
    self.playerDict = {}
    self.bulletList = []

    return self.observations

  def render(self, screen):
    wall_color = pygame.Color('#4139db')
    pygame.draw.rect(screen, wall_color, (0, 0, conf['WALL_WIDTH'], conf['SPACE_HEIGHT']))
    pygame.draw.rect(screen, wall_color, (0, 0, conf['SPACE_WIDTH'], conf['WALL_WIDTH']))
    pygame.draw.rect(screen, wall_color, (conf['SPACE_WIDTH'] - conf['WALL_WIDTH'], 0, conf['WALL_WIDTH'], conf['SPACE_HEIGHT']))
    pygame.draw.rect(screen, wall_color, (0, conf['SPACE_HEIGHT'] - conf['WALL_WIDTH'], conf['SPACE_WIDTH'], conf['WALL_WIDTH']))

    for id in self.playerDict:
      player = self.playerDict[id]
      player.draw(screen)

      # Outside Player.draw() for score flexibility (ex: team scores)
      if (show_score):
        info = str(self.scores[id])
        font = pygame.font.Font('freesansbold.ttf', 12) 
        text = font.render(info, True, pygame.Color('#efefef')) 
        textRect = text.get_rect()  
        textRect.center = (player.x, player.y + conf['PLAYER_RADIUS'] + 10) 
        screen.blit(text, textRect)

    for o in self.bulletList:
      o.draw(screen)

class StaticPelletEnv(PelletEnv):
  def reset(self):
    self.scores = {}
    self.alive = {}
    self.actionLog = None
    self.playerCount = 0
    self.t = 0
    self.done = False
    self.observations = {}
    self.playerDict = {}
    self.bulletList = []
    
    conf['NUM_LIVES'] = 1

    self.addPlayer(100, conf['SPACE_HEIGHT'] // 2, False)
    self.addPlayer(conf['SPACE_WIDTH'] - 100, conf['SPACE_HEIGHT'] // 2, False)
    self.addPlayer(200, 400, False)

    return self.observations

# Polar to rectangular coordinates helper
def polarToRect(r, theta):
  return (r * np.cos(theta), r * np.sin(theta))

# Within bounds helper
def within(cx, cy, d, ox, oy, r):
  if ((ox + r >= cx - d and ox - r <= cx + d) and
    (oy + r >= cy - d and oy - r <= cy + d)):
    return True
  return False

class Circle:
  def __init__(self, x, y, r):
    self.x = x
    self.y = y
    self.r = r
    self.vx = 0
    self.vy = 0
    self.ax = 0
    self.ay = 0

  def update(self):
    self.vx += self.ax
    self.vy += self.ay
    self.x += self.vx
    self.y += self.vy

  def draw(self, screen, color):
    color = pygame.Color(color)
    x = int(np.round(self.x))
    y = int(np.round(self.y))
    r = int(np.round(self.r))
    pygame.draw.circle(screen, color, (x, y), r)

class Player(Circle):
  def __init__(self, x, y, env, playerID, isHuman=False):
    super().__init__(x, y, conf['PLAYER_RADIUS'])
    self.env = env
    self.id = playerID
    self.isHuman = isHuman
    self.cooldown = conf['FIRE_COOLDOWN']
    self.lives = conf['NUM_LIVES']
    self.fov = FOV(env, self)

  def update(self, action):
    self.ax = 0
    self.ay = 0

    # No corpse physics better for performance
    if (self.lives == 0):
      self.vx = 0
      self.vy = 0
      return

    if (action[0]):
      self.ay -= conf['INPUT_FORCE']
    if (action[1]):
      self.ay += conf['INPUT_FORCE']
    if (action[2]):
      self.ax -= conf['INPUT_FORCE']
    if (action[3]):
      self.ax += conf['INPUT_FORCE']

    # Apply friction
    if (self.vx > 0):
      self.ax -= conf['FRICTION_FORCE']
    elif (self.vx < 0):
      self.ax += conf['FRICTION_FORCE']
    if (self.vy > 0):
      self.ay -= conf['FRICTION_FORCE']
    elif (self.vy < 0):
      self.ay += conf['FRICTION_FORCE']

    self.vx += self.ax
    self.vy += self.ay

    # Clip to max player velocity
    c = np.sqrt(np.square(self.vx) + np.square(self.vy))
    if (c > conf['PLAYER_MAX_VEL']):
      f = c / conf['PLAYER_MAX_VEL']
      self.vx /= f
      self.vy /= f

    # Eliminate residual movement
    if (np.abs(self.vx) < conf['VEL_KILL_EPSILON']):
      self.vx = 0
    if (np.abs(self.vy) < conf['VEL_KILL_EPSILON']):
      self.vy = 0

    # Bound movement to walls
    if ((self.x > conf['WALL_WIDTH'] + conf['PLAYER_RADIUS'] or self.vx > 0) and
        (self.x < conf['SPACE_WIDTH'] - conf['WALL_WIDTH'] - conf['PLAYER_RADIUS'] or self.vx < 0)):
      self.x += self.vx
    if ((self.y > conf['WALL_WIDTH'] + conf['PLAYER_RADIUS'] or self.vy > 0) and
        (self.y < conf['SPACE_HEIGHT'] - conf['WALL_WIDTH'] - conf['PLAYER_RADIUS'] or self.vy < 0)):
      self.y += self.vy

    if (self.cooldown > 0):
      self.cooldown -= 1

    # Handle firing
    if (action[4] and self.cooldown == 0):
      self.cooldown = conf['FIRE_COOLDOWN']

      theta = action[5]
      if (self.isHuman and pygame is not None):
        mouseX, mouseY = pygame.mouse.get_pos()
        theta = np.arctan((mouseY - self.y) / (mouseX - self.x))
        if (self.x > mouseX):
          theta += np.pi

      Bullet(self.x, self.y, theta, self.env, self.id)

  def kill(self):
    if (self.lives > 0):
      self.lives -= 1

  # Untethered from update() so all agents can see equilibrium state
  def updateFOV(self):
    self.fov.update()

  def draw(self, screen):
    if (show_fov and self.lives > 0):
      self.fov.draw(screen)

    player_color = '#c22b5b'

    # Draw aim line if human player
    if (self.isHuman and self.lives > 0):
      player_color = '#f7d474'
      sight_color = pygame.Color('#842eff')
      mouseX, mouseY = pygame.mouse.get_pos()
      pygame.draw.aaline(screen, sight_color, (self.x, self.y), (mouseX, mouseY))
      pygame.draw.circle(screen, sight_color, (mouseX, mouseY), 6)

    if (self.lives == 0):
      player_color = '#898989'

    super().draw(screen, player_color)

    # Draw velocity indicator
    indicator_color = pygame.Color('#42e0ff')
    toX = self.x + 3 * self.vx
    toY = self.y + 3 * self.vy
    pygame.draw.line(screen, indicator_color, (self.x, self.y), (toX, toY), 2)

class FOV():
  def __init__(self, env, player):
    self.env = env
    self.player = player
    self.grid = np.zeros((2 * conf['GRID_RADIUS'], 2 * conf['GRID_RADIUS']))
    self.mem = self.grid

  # Approximates with square objects (players and bullets) for performance
  def update(self):

    # For performance, filter to bullets and living players (for now) in FOV grid
    filteredPlayers = set()
    filteredBullets = set()
    me = self.player
    d = conf['FOV_DISTANCE']
    for id in self.env.playerDict:
      if (id != me.id):
        player = self.env.playerDict[id]
        if (within(me.x, me.y, d, player.x, player.y, conf['PLAYER_RADIUS']) 
          and player.lives > 0):
          filteredPlayers.add(player)
    for i in range(len(self.env.bulletList)):
      bullet = self.env.bulletList[i]
      if (within(me.x, me.y, d, bullet.x, bullet.y, conf['BULLET_RADIUS'])):
        filteredBullets.add(bullet)

    # Reset FOV grid
    self.mem = self.grid
    self.grid = np.zeros((2 * conf['GRID_RADIUS'], 2 * conf['GRID_RADIUS']))

    for i in range(2 * conf['GRID_RADIUS']):
      for j in range(2 * conf['GRID_RADIUS']):
        cell_d = conf['FOV_DISTANCE'] / conf['GRID_RADIUS']
        cx = self.player.x - conf['FOV_DISTANCE'] + (i * cell_d) + (cell_d / 2)
        cy = self.player.y - conf['FOV_DISTANCE'] + (j * cell_d) + (cell_d / 2)
        cr = cell_d / 2

        if (cx < conf['WALL_WIDTH'] or cx > conf['SPACE_WIDTH'] - conf['WALL_WIDTH'] or
          cy < conf['WALL_WIDTH'] or cy > conf['SPACE_HEIGHT'] - conf['WALL_WIDTH']):

          self.grid[j][i] = 4
          continue

        for bullet in filteredBullets:
          if (within(cx, cy, cr, bullet.x, bullet.y, conf['BULLET_RADIUS'])):
            if (bullet.playerID == me.id):
              self.grid[j][i] = 2
              break
            else:
              self.grid[j][i] = 3
              break

        # Player presence overrides bullet presence 
        for player in filteredPlayers:
          if (within(cx, cy, cr, player.x, player.y, conf['PLAYER_RADIUS'])):
            self.grid[j][i] = 1
            break

  def draw(self, screen):
    grid_color = pygame.Color('#e44d7d')
    bullet_color = pygame.Color('#f0ae46')
    own_bullet_color = pygame.Color('#2cdb92')
    enemy_color = pygame.Color('#a47dff')
    wall_color = pygame.Color('#efefef')

    for i in range(2 * conf['GRID_RADIUS']):
      for j in range(2 * conf['GRID_RADIUS']):
        cell_d = conf['FOV_DISTANCE'] / conf['GRID_RADIUS']
        corner_x = self.player.x - conf['FOV_DISTANCE'] + (i * cell_d)
        corner_y = self.player.y - conf['FOV_DISTANCE'] + (j * cell_d)

        # Not consolidated to allow for outline vs. fill
        if (self.grid[j][i] == 0):
          pygame.draw.rect(screen, grid_color, (corner_x, corner_y, cell_d, cell_d), 2)
        elif (self.grid[j][i] == 1):
          pygame.draw.rect(screen, enemy_color, (corner_x, corner_y, cell_d, cell_d))
        elif (self.grid[j][i] == 2):
          pygame.draw.rect(screen, own_bullet_color, (corner_x, corner_y, cell_d, cell_d))
        elif (self.grid[j][i] == 3):
          pygame.draw.rect(screen, bullet_color, (corner_x, corner_y, cell_d, cell_d))
        elif (self.grid[j][i] == 4):
          pygame.draw.rect(screen, wall_color, (corner_x, corner_y, cell_d, cell_d))

class Bullet(Circle):
  def __init__(self, x, y, theta, env, playerID):
    super().__init__(x, y, conf['BULLET_RADIUS'])
    self.vx, self.vy = polarToRect(conf['BULLET_VEL'], theta)
    self.env = env
    self.playerID = playerID

    self.env.bulletList.append(self)

  def update(self):
    super().update()

    # Clear if out of bounds
    if (self.x < conf['WALL_WIDTH'] or self.x > conf['SPACE_WIDTH'] - conf['WALL_WIDTH'] or
        self.y < conf['WALL_WIDTH'] or self.y > conf['SPACE_HEIGHT'] - conf['WALL_WIDTH']):
      self.env.bulletList.remove(self)
      return 

    # Check for bullet collision (can reallocate some functionality to env)
    for id in self.env.playerDict:
      player = self.env.playerDict[id]
      if (np.square(self.x - player.x) + np.square(self.y - player.y) < 
        np.square(conf['PLAYER_RADIUS']) and self.playerID != player.id):

        # No points for hitting a dead player
        if (player.lives > 0):
          player.kill()
          
          # Update list of living playrs and check game over
          if (player.lives == 0):
            self.env.alive[id] = 0
          if (sum(self.env.alive.values()) == 1):
            self.env.done = True

          self.env.scores[self.playerID] += 500
          self.env.scores[id] -= 1000
          self.env.bulletList.remove(self)

  def draw(self, screen):
    super().draw(screen, '#ff61df')