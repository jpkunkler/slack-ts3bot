import re
import time
import ts3
import json
from slackclient import SlackClient
import datetime as dt

from credentials import *
import sys
sys.stdout.buffer.write(chr(9986).encode('utf8'))

def main():
    """main() will connect to slack and ts3 and then initialize the main loop"""
    # slack connection
    slack = SlackClient(apiToken)

    # ts3 connection
    conn = ts3.TS3Server(ts_ip, query_port)
    conn.login(ts_admin, ts_pw)
    servers = conn.send_command('serverlist').data

    #  get bot user id
    user_list = slack.api_call("users.list")
    for user in user_list.get("members"):
        if user.get("name") == "ts3bot":
            slack_user_id = user.get("id")
            break

    if slack.rtm_connect():
        print("Connected!")

    while True:
        for message in slack.rtm_read():
            if "text" in message and message["text"].startswith("<@{}".format(slack_user_id)):
                print("Message received: {}".format(json.dumps(message, indent=2)))
                message_text = message["text"]

                # if message contains user(s) or client(s)
                if re.match(r".*(client)(s\b|\b).*|.*(user)(s\b|\b).*|.*(!clientlist).*",
                    message_text, re.IGNORECASE):
                    clientlist(conn, slack, message, servers)

                # server uptime
                if re.match(r".*(!uptime).*", message_text, re.IGNORECASE):
                    uptime(conn, slack, message)
            
        time.sleep(1)

def clientlist(conn, slack, msg, servers):
    """clientlist will list all clients currently connected to the ts3 server"""
    clients = []
    for server in servers:
        conn.use(server['virtualserver_id'])
        all_clients = conn.send_command('clientlist').data
        for client in all_clients:
            if not 'serveradmin' in client['client_nickname']:
                nickname = client['client_nickname']
                clients.append(nickname)

    client_text = "Currently {} client(s) online:\n\n".format(len(clients)) + "\n".join(str(p) for p in clients)
    slack.api_call(
        "chat.postMessage",
        channel=msg["channel"],
        text=client_text,
        as_user=True)
    
def uptime(conn, slack, msg):
    """uptime returns the current uptime of the ts3 instance or an error if the instance is offline"""
    try:
        hostinfo = conn.send_command("hostinfo").data
        server_uptime = str(dt.timedelta(seconds=int(hostinfo[0]["instance_uptime"])))

        slack.api_call(
            "chat.postMessage",
            channel=msg["channel"],
            text="Server is up for {}.".format(server_uptime),
            as_user=True)
    except:
        slack.api_call(
            "chat.postMessage",
            channel=msg["channel"],
            text="Server is currently offline!",
            as_user=True)

if __name__ == "__main__":
    main()