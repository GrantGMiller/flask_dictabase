import random
import string

from flask import (
    Flask,
    request,
)
import flask_dictabase

app = Flask('User Management')
# if you would like to specify the SQLAlchemy database then you can do:
# app.config['DATABASE_URL'] = 'sqlite:///my.db'
app.db = flask_dictabase.Dictabase(app)


@app.route('/set/<key>/<value>')
def Set(key, value):
    app.db.var.Set(key, value)
    return f'Set {key}={value}'


@app.route('/get/<key>')
def Get(key):
    return app.db.var.Get(key)


class Player(flask_dictabase.BaseTable):
    pass


class Card(flask_dictabase.BaseTable):
    pass


with app.app_context():
    SUITS = ['club', 'spade', 'heart', 'diamond']
    VALUES = ['ace', 'jack', 'queen', 'king'] + [i for i in range(2, 10 + 1)]

    player = app.db.NewOrFind(Player, name='Grant')
    print('player=', player)

    # create all the cards in the database
    for suit in SUITS:
        for value in VALUES:
            app.db.NewOrFind(Card, suit=suit, value=value)

    # give the player some cards
    for i in range(5):
        suit = random.choice(SUITS)
        value = random.choice(VALUES)

        player.Link(
            app.db.NewOrFind(Card, suit=suit, value=value)
        )

    print('The cards in the players hand are:')
    for card in player.Links(Card):
        print('card=', card)

    print('the player is holding the following cards that are hearts')
    for card in player.Links(Card, suit='heart'):
        print('card=', card)

    for index, obj in enumerate(player.Links(Card)):
        if index % 3 == 0:
            player.Unlink(obj)
            print('player discarded the card=', obj)

    card = app.db.NewOrFind(Card, suit='heart', value='queen')
    for obj in card.Links():
        print('the queen of hearts is held by player=', obj)

if __name__ == '__main__':
    app.run(debug=True)
