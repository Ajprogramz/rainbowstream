"""
Colorful user's timeline stream
"""
from multiprocessing import Process
from dateutil import parser

import os
import os.path
import sys
import signal
import argparse
import time
import datetime

from twitter.stream import TwitterStream, Timeout, HeartbeatTimeout, Hangup
from twitter.api import *
from twitter.oauth import OAuth, read_token_file
from twitter.oauth_dance import oauth_dance
from twitter.util import printNicely

from .colors import *
from .config import *
from .interactive import *
from .db import *

g = {}
db = RainbowDB()
cmdset = [
    'switch',
    'home',
    'view',
    't',
    'rt',
    'rep',
    'del',
    's',
    'fr',
    'fl',
    'h',
    'c',
    'q'
]


def draw(t, keyword=None, fil=[], ig=[]):
    """
    Draw the rainbow
    """

    # Retrieve tweet
    tid = t['id']
    text = t['text']
    screen_name = t['user']['screen_name']
    name = t['user']['name']
    created_at = t['created_at']
    date = parser.parse(created_at)
    date = date - datetime.timedelta(seconds=time.timezone)
    clock = date.strftime('%Y/%m/%d %H:%M:%S')

    # Filter and ignore
    screen_name = '@' + screen_name
    if fil and screen_name not in fil:
        return
    if ig and screen_name in ig:
        return

    res = db.tweet_query(tid)
    if not res:
        db.store(tid)
        res = db.tweet_query(tid)
    rid = res[0].rainbow_id

    # Format info
    user = cycle_color(name) + grey(' ' + screen_name + ' ')
    meta = grey('[' + clock + '] [id=' + str(rid) + ']')
    tweet = text.split()
    # Highlight RT
    tweet = map(lambda x: grey(x) if x == 'RT' else x, tweet)
    # Highlight screen_name
    tweet = map(lambda x: cycle_color(x) if x[0] == '@' else x, tweet)
    # Highlight link
    tweet = map(lambda x: cyan(x) if x[0:7] == 'http://' else x, tweet)
    # Highlight search keyword
    if keyword:
        tweet = map(
            lambda x: on_yellow(x) if
            ''.join(c for c in x if c.isalnum()).lower() == keyword.lower()
            else x,
            tweet
        )
    tweet = ' '.join(tweet)

    # Draw rainbow
    line1 = u"{u:>{uw}}:".format(
        u=user,
        uw=len(user) + 2,
    )
    line2 = u"{c:>{cw}}".format(
        c=meta,
        cw=len(meta) + 2,
    )
    line3 = '  ' + tweet

    printNicely('')
    printNicely(line1)
    printNicely(line2)
    printNicely(line3)


def parse_arguments():
    """
    Parse the arguments
    """
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        '-to',
        '--timeout',
        help='Timeout for the stream (seconds).')
    parser.add_argument(
        '-ht',
        '--heartbeat-timeout',
        help='Set heartbeat timeout.',
        default=90)
    parser.add_argument(
        '-nb',
        '--no-block',
        action='store_true',
        help='Set stream to non-blocking.')
    parser.add_argument(
        '-tt',
        '--track-keywords',
        help='Search the stream for specific text.')
    parser.add_argument(
        '-fil',
        '--filter',
        help='Filter specific screen_name.')
    parser.add_argument(
        '-ig',
        '--ignore',
        help='Ignore specific screen_name.')
    return parser.parse_args()


def authen():
    """
    Authenticate with Twitter OAuth
    """
    # When using rainbow stream you must authorize.
    twitter_credential = os.environ.get(
        'HOME',
        os.environ.get(
            'USERPROFILE',
            '')) + os.sep + '.rainbow_oauth'
    if not os.path.exists(twitter_credential):
        oauth_dance("Rainbow Stream",
                    CONSUMER_KEY,
                    CONSUMER_SECRET,
                    twitter_credential)
    oauth_token, oauth_token_secret = read_token_file(twitter_credential)
    return OAuth(
        oauth_token,
        oauth_token_secret,
        CONSUMER_KEY,
        CONSUMER_SECRET)


def get_decorated_name():
    """
    Beginning of every line
    """
    t = Twitter(auth=authen())
    name = '@' + t.account.verify_credentials()['screen_name']
    g['original_name'] = name[1:]
    g['decorated_name'] = grey('[') + grey(name) + grey(']: ')


def switch():
    """
    Switch stream
    """
    try:
        target = g['stuff'].split()[0]

        # Filter and ignore
        args = parse_arguments()
        try :
            if g['stuff'].split()[-1] == '-f':
                only = raw_input('Only nicks: ')
                ignore = raw_input('Ignore nicks: ')
                args.filter = filter(None,only.split(','))
                args.ignore = filter(None,ignore.split(','))
            elif g['stuff'].split()[-1] == '-d':
                args.filter = ONLY_LIST
                args.ignore = IGNORE_LIST
        except:
            printNicely(red('Sorry, wrong format.'))
            return

        # Public stream
        if target == 'public':
            keyword = g['stuff'].split()[1]
            if keyword[0] == '#':
                keyword = keyword[1:]
            # Kill old process
            os.kill(g['stream_pid'], signal.SIGKILL)
            args.track_keywords = keyword
            # Start new process
            p = Process(
                target=stream,
                args=(
                    PUBLIC_DOMAIN,
                    args))
            p.start()
            g['stream_pid'] = p.pid

        # Personal stream
        elif target == 'mine':
            # Kill old process
            os.kill(g['stream_pid'], signal.SIGKILL)
            # Start new process
            p = Process(
                target=stream,
                args=(
                    USER_DOMAIN,
                    args,
                    g['original_name']))
            p.start()
            g['stream_pid'] = p.pid
        printNicely('')
        printNicely(green('Stream switched.'))
        if args.filter:
            printNicely(cyan('Only: ' + str(args.filter)))
        if args.ignore:
            printNicely(red('Ignore: ' + str(args.ignore)))
        printNicely('')
    except:
        printNicely(red('Sorry I can\'t understand.'))


def home():
    """
    Home
    """
    t = Twitter(auth=authen())
    num = HOME_TWEET_NUM
    if g['stuff'].isdigit():
        num = g['stuff']
    for tweet in reversed(t.statuses.home_timeline(count=num)):
        draw(t=tweet)
    printNicely('')


def view():
    """
    Friend view
    """
    t = Twitter(auth=authen())
    user = g['stuff'].split()[0]
    if user[0] == '@':
        try:
            num = int(g['stuff'].split()[1])
        except:
            num = HOME_TWEET_NUM
        for tweet in reversed(t.statuses.user_timeline(count=num, screen_name=user[1:])):
            draw(t=tweet)
        printNicely('')
    else:
        printNicely(red('A name should begin with a \'@\''))


def tweet():
    """
    Tweet
    """
    t = Twitter(auth=authen())
    t.statuses.update(status=g['stuff'])


def retweet():
    """
    ReTweet
    """
    t = Twitter(auth=authen())
    try:
        id = int(g['stuff'].split()[0])
        tid = db.rainbow_query(id)[0].tweet_id
        t.statuses.retweet(id=tid, include_entities=False, trim_user=True)
    except:
        printNicely(red('Sorry I can\'t retweet for you.'))


def reply():
    """
    Reply
    """
    t = Twitter(auth=authen())
    try:
        id = int(g['stuff'].split()[0])
        tid = db.rainbow_query(id)[0].tweet_id
        user = t.statuses.show(id=tid)['user']['screen_name']
        status = ' '.join(g['stuff'].split()[1:])
        status = '@' + user + ' ' + status.decode('utf-8')
        t.statuses.update(status=status, in_reply_to_status_id=tid)
    except:
        printNicely(red('Sorry I can\'t understand.'))


def delete():
    """
    Delete
    """
    t = Twitter(auth=authen())
    try:
        id = int(g['stuff'].split()[0])
        tid = db.rainbow_query(id)[0].tweet_id
        t.statuses.destroy(id=tid)
        printNicely(green('Okay it\'s gone.'))
    except:
        printNicely(red('Sorry I can\'t delete this tweet for you.'))


def search():
    """
    Search
    """
    t = Twitter(auth=authen())
    try:
        if g['stuff'][0] == '#':
            rel = t.search.tweets(q=g['stuff'])['statuses']
            if len(rel):
                printNicely('Newest tweets:')
                for i in reversed(xrange(SEARCH_MAX_RECORD)):
                    draw(t=rel[i], keyword=g['stuff'].strip()[1:])
                printNicely('')
            else:
                printNicely(magenta('I\'m afraid there is no result'))
        else:
            printNicely(red('A keyword should be a hashtag (like \'#AKB48\')'))
    except:
        printNicely(red('Sorry I can\'t understand.'))


def friend():
    """
    List of friend (following)
    """
    t = Twitter(auth=authen())
    g['friends'] = t.friends.ids()['ids']
    for i in g['friends']:
        name = t.users.lookup(user_id=i)[0]['name']
        screen_name = '@' + t.users.lookup(user_id=i)[0]['screen_name']
        user = cycle_color(name) + grey(' ' + screen_name + ' ')
        print user


def follower():
    """
    List of follower
    """
    t = Twitter(auth=authen())
    g['followers'] = t.followers.ids()['ids']
    for i in g['followers']:
        name = t.users.lookup(user_id=i)[0]['name']
        screen_name = '@' + t.users.lookup(user_id=i)[0]['screen_name']
        user = cycle_color(name) + grey(' ' + screen_name + ' ')
        print user


def help():
    """
    Help
    """
    usage = '''
    Hi boss! I'm ready to serve you right now!
    -------------------------------------------------------------
    You are already on your personal stream:
      "switch public #AKB" will switch to public stream and follow "AKB" keyword.
      "switch mine" will switch back to your personal stream.
      "switch mine -f" will prompt to enter the filter.
        "Only nicks" filter will decide nicks will be INCLUDE ONLY.
        "Ignore nicks" filter will decide nicks will be EXCLUDE.
      "switch mine -d" will use the config's ONLY_LIST and IGNORE_LIST
        (see rainbowstream/config.py).
    For more action:
      "home" will show your timeline. "home 7" will show 7 tweet.
      "view @bob" will show your friend @bob's home.
      "t oops" will tweet "oops" immediately.
      "rt 12345" will retweet to tweet with id "12345".
      "rep 12345 oops" will reply "oops" to tweet with id "12345".
      "del 12345" will delete tweet with id "12345".
      "s #AKB48" will search for "AKB48" and return 5 newest tweet.
      "fr" will list out your following people.
      "fl" will list out your followers.
      "h" will show this help again.
      "c" will clear the terminal.
      "q" will exit.
    -------------------------------------------------------------
    Have fun and hang tight!
    '''
    printNicely(usage)


def clear():
    """
    Clear screen
    """
    os.system('clear')


def quit():
    """
    Exit all
    """
    os.system('rm -rf rainbow.db')
    os.kill(g['stream_pid'], signal.SIGKILL)
    sys.exit()


def reset():
    """
    Reset prefix of line
    """
    if g['reset']:
        printNicely(green('Need tips ? Type "h" and hit Enter key!'))
    g['reset'] = False


def process(cmd):
    """
    Process switch
    """
    return dict(zip(
        cmdset,
        [
            switch,
            home,
            view,
            tweet,
            retweet,
            reply,
            delete,
            search,
            friend,
            follower,
            help,
            clear,
            quit
        ]
    )).get(cmd, reset)


def listen():
    """
    Listen to user's input
    """
    d = dict(zip(
        cmdset,
        [
            ['public #','mine'], # switch
            [], # home
            ['@'], # view
            [], # tweet
            [], # retweet
            [], # reply
            [], # delete
            ['#'], # search
            [], # friend
            [], # follower
            [], # help
            [], # clear
            [], # quit
        ]
        ))
    init_interactive_shell(d)
    reset()
    while True:
        if g['prefix']:
            line = raw_input(g['decorated_name'])
        else:
            line = raw_input()
        try:
            cmd = line.split()[0]
        except:
            cmd = ''
        # Save cmd to global variable and call process
        g['stuff'] = ' '.join(line.split()[1:])
        process(cmd)()
        if cmd in ['switch','t','rt','rep']:
            g['prefix'] = False
        else:
            g['prefix'] = True


def stream(domain, args, name='Rainbow Stream'):
    """
    Track the stream
    """

    # The Logo
    art_dict = {
        USER_DOMAIN: name,
        PUBLIC_DOMAIN: args.track_keywords,
        SITE_DOMAIN: 'Site Stream',
    }
    ascii_art(art_dict[domain])

    # These arguments are optional:
    stream_args = dict(
        timeout=args.timeout,
        block=not args.no_block,
        heartbeat_timeout=args.heartbeat_timeout)

    # Track keyword
    query_args = dict()
    if args.track_keywords:
        query_args['track'] = args.track_keywords

    # Get stream
    stream = TwitterStream(
        auth=authen(),
        domain=domain,
        **stream_args)

    if domain == USER_DOMAIN:
        tweet_iter = stream.user(**query_args)
    elif domain == SITE_DOMAIN:
        tweet_iter = stream.site(**query_args)
    else:
        if args.track_keywords:
            tweet_iter = stream.statuses.filter(**query_args)
        else:
            tweet_iter = stream.statuses.sample()

    # Iterate over the stream.
    for tweet in tweet_iter:
        if tweet is None:
            printNicely("-- None --")
        elif tweet is Timeout:
            printNicely("-- Timeout --")
        elif tweet is HeartbeatTimeout:
            printNicely("-- Heartbeat Timeout --")
        elif tweet is Hangup:
            printNicely("-- Hangup --")
        elif tweet.get('text'):
            draw(t=tweet, keyword=args.track_keywords, fil=args.filter, ig=args.ignore)


def fly():
    """
    Main function
    """
    # Spawn stream process
    args = parse_arguments()
    get_decorated_name()
    p = Process(target=stream, args=(USER_DOMAIN, args, g['original_name']))
    p.start()

    # Start listen process
    time.sleep(0.5)
    g['reset'] = True
    g['prefix'] = True
    g['stream_pid'] = p.pid
    listen()

