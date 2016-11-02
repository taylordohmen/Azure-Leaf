# author(s): Taylor Dohmen, Alex Priest, James Murphy
import psycopg2
import psycopg2.extras
from hashlib import md5
from random import randrange

# names of fields for data verification purposes
# made immutable and moved to global scope for function legibility
abilities = (
    'strength', 'constitution', 'dexterity',
    'intelligence', 'wisdom', 'charisma'
)
    
skills = (
    'Athletics', 'Acrobatics', 'Sleight_of_Hand', 'Stealth',
    'Arcana', 'History', 'Investigation', 'Nature', 'Religion',
    'Animal_Handling', 'Insight', 'Medicine', 'Perception',
    'Survival', 'Deception', 'Intimidation', 'Performance',
    'Persuasion'
)

static_character_data = ('name', 'class', 'race')

class AuthenticationException(Exception):
    pass

class CharacterCreationException(Exception):
    pass

def connectToDB():
    connectionStr = 'dbname=azure_leaf user=azure password=123 host=localhost'
    try:
        return psycopg2.connect(connectionStr)
    except:
        print("Can't connect to database")
        
def isUserAvailable(username):
    """ Queries the database for the presence of `username`
        returns False if not present, True otherwise
    """
    conn = connectToDB()
    if conn == None:
        raise Exception("Database connection failed.")
    cur = conn.cursor()
    
    # James' SQL contribution
    query = cur.mogrify("SELECT username FROM users WHERE username = %s", (username,))
    cur.execute(query)
    results = cur.fetchall()
    return not bool(results)
    
def createNewUser(username, password, is_dm):
    """ Inserts new user into database if username is available and password is
        valid.
    """
    if not username or not password:
        raise AuthenticationException("Username or password was left blank.")
    if not isUserAvailable(username):
        raise AuthenticationException("Username is not available.") 
    
    conn = connectToDB()
    cur = conn.cursor()
    
    # is_dm is a boolean, we must make it a '1' or '0' for psql BIT datatype
    # Taylor's SQL contribution
    query = cur.mogrify("INSERT INTO users VALUES (%s, crypt(%s, gen_salt('bf')), %s);", (username, password, str(int(is_dm))))
    cur.execute(query)
    conn.commit()
    return 0
    
def authenticate(username, password):
    """ Attempt to authenticate user with `username`, `password` """
    if not username or not password:
        raise AuthenticationException("Username or password was left blank.")
    conn = connectToDB()
    cur = conn.cursor()
    
    # Alex's SQL contribution
    query = cur.mogrify("SELECT username FROM users WHERE username = %s AND password = crypt(%s, password);", (username, password))
    cur.execute(query)
    results = cur.fetchall()
    if not bool(results):
        raise AuthenticationException("Incorrect username or password.")
    return results

def createNewCharacter(user, attr): # Using dicts as god objects? Well, it could be worse. We could be enterprise Java devs.
    """ Inserts a new character into the database """
    
    conn = connectToDB()
    cur = conn.cursor()
    
    # declaration unnecessary, but made as a reminder that these
    # tuples are global and immutable, but used here
    global abilities
    global skills
    global static_character_data
    
    # guarantee correct type for skills
    for skill in skills:
        if skill not in attr:
            attr[skill] = '0'
        else:
            attr[skill] = '1'
            
    # un-nest ability score values
    for abil in abilities:
        attr[abil] = int(attr[abil][0])
    
    # un-nest character name, race, and class values
    for datum in static_character_data:
        attr[datum] = attr[datum][0]
    
    # character must have a name
    if not attr['name']:
        raise CharacterCreationException("Character name left blank.")
    
    # generate the correct number of comma-separated %s format substrings for impending mogrify() call
    mog_number = bool(user) + len(attr)
    mog = "(" + ', '.join(['%s'] * mog_number) + ");"
    
    # create (fields, ...) for INSERT statement formatting
    fields = '(' + ', '.join(attr.keys() + ["username"]) + ')'
    
    # create matching VALUES for INSERT statement
    values = tuple(attr.values() + [user])
    
    qformat = "INSERT INTO characters %s VALUES " % fields
    query = cur.mogrify(qformat + mog, values)
    cur.execute(query)
    conn.commit()
    return 0
    
def generateAbility(player=True):
    """ Returns a randomly generated integer between 3 and 18, or
        8 and 18 if character is a player or DMPC, which is the default case.
        Monster stat blocks can have lower values.
    """
    score = 0
    threshold = [3,7][player]
    while score < threshold: # ability scores below 7 suck a lot for player characters
        rolls = []
        for d in xrange(4): # looping variable `d` unused as it is mathematically irrelevant.
            rolls.append(randrange(6) + 1)
        rolls.remove(min(rolls))
        score = sum(rolls)
    return score
    
def proficiencyBonus(level, expertise=False):
    """ Return proficiency bonus for a given level to apply to a skill. """
    prof = (level - 1) / 4 # proficiency is a step function
    prof += 2 # base proficiency bonus is +2
    prof *= [1, 2][expertise] # expertise is x2 multiplier
    return prof
    
def abilityModifier(score):
    return (score - 10) / 2;
    
def createMessage(username, message, related_post):
    """ Adds a new message to the message table """
    db = connectToDB()
    cur = db.cursor()
    query = cur.mogrify('insert into messages (author, body, related_post, date_posted) values (%s, %s, %s, current_timestamp);',
                        (username, message, related_post))
    try:
        cur.execute(query)
    except Exception as e:
        db.rollback()
        print(e)
    db.commit()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = cur.mogrify('select author, body, date_posted from messages order by date_posted desc limit 1;')
    cur.execute(query)
    return cur.fetchone()

def getMessages(room): # TODO: args
    """ Retrieves messages from database based on {INSERT ARGS HERE} """
    db = connectToDB()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = cur.mogrify("select author, body, date_posted from messages where related_post = %s;", (room,))
    try:
        cur.execute(query)
    except Exception as e:
        print(e)
        
    temp = cur.fetchall()
    if temp: 
        # print(temp)
        return temp
    else: return {}
