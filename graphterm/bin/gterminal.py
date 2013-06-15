#!/usr/bin/env python

"""gterminal: GraphTerm client launcher
"""

import hashlib
import hmac
import logging
import os
import random
import sys

import tornado.httpclient

import gterm

Http_addr = "localhost"
Http_port = gterm.DEFAULT_HTTP_PORT

def getuid(pid):
    """Return uid of running process"""
    command_args = ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fu"]
    std_out, std_err = gterm.command_output(command_args, timeout=1)
    if std_err:
        logging.warning("getuid: ERROR %s", std_err)
        return None
    try:
        return int(std_out.split("\n")[1][1:])
    except Exception, excp:
        logging.warning("getuid: ERROR %s", excp)
        return None

def auth_request(http_addr, http_port, nonce, timeout=None, client_auth=False, user="", protocol="http"):
    """Simulate user form submission by executing a HTTP request"""

    cert_dir = gterm.App_dir
    server_name = "localhost"
    client_prefix = server_name + "-gterm-local"
    ca_certs = cert_dir+"/"+server_name+".crt"
    
    ssl_options = {}
    if client_auth:
	client_cert = cert_dir+"/"+client_prefix+".crt"
	client_key = cert_dir+"/"+client_prefix+".key"
	ssl_options.update(client_cert=client_cert, client_key=client_key)
	
    url = "%s://%s:%s/_auth/?nonce=%s" % (protocol, http_addr, http_port, nonce)
    if user:
        url += "&user=" + user
    request = tornado.httpclient.HTTPRequest(url, validate_cert=True, ca_certs=ca_certs,
					     **ssl_options)
    http_client = tornado.httpclient.HTTPClient()
    try:
	response = http_client.fetch(request)
	if response.error:
	    print >> sys.stderr, "HTTPClient ERROR response.error ", response.error
	    return None
	return response.body
    except tornado.httpclient.HTTPError, excp:
	print >> sys.stderr, "HTTPClient ERROR ", excp
    return None

def auth_token(secret, connection_id, client_nonce, server_nonce):
    """Return (client_token, server_token)"""
    SIGN_SEP = "|"
    prefix = SIGN_SEP.join([connection_id, client_nonce, server_nonce]) + SIGN_SEP
    return [hmac.new(str(secret), prefix+conn_type, digestmod=hashlib.sha256).hexdigest()[:24] for conn_type in ("client", "server")]

def main():
    global Http_addr, Http_port
    from optparse import OptionParser
    usage = "usage: gterm [-h ... options] [[host/]session]"
    parser = OptionParser(usage=usage)

    parser.add_option("", "--https", dest="https", action="store_true",
                      help="Use SSL (TLS) connections for security")
    parser.add_option("-n", "--noauth", dest="noauth", action="store_true",
                      help="No authentication required")
    parser.add_option("-b", "--browser", dest="browser", default="",
                      help="Browser application name (OS X only)")
    parser.add_option("-u", "--user", dest="user", default="",
                      help="User name")
    parser.add_option("-s", "--server", dest="server", default="",
                      help="Remote server domain name")
    parser.add_option("-p", "--port", dest="port", default=0,
                      help="Remote server port", type="int")
    parser.add_option("", "--client_cert", dest="client_cert", default="",
                      help="Path to client CA cert (or '.')")
    #parser.add_option("", "--term_type", dest="term_type", default="",
    #                  help="Terminal type (linux/screen/xterm) NOT YET IMPLEMENTED")

    (options, args) = parser.parse_args()
    protocol = "https" if options.https else "http"

    path = ""
    if args:
        if "/" in args[0]:
            path = args[0]
        else:
            path = (gterm.Host or "local") + "/" + args[0]

    if not options.server and gterm.Lterm_cookie:
        # Open new terminal window from within graphterm window
        path = path or (gterm.Host + "/" + "new")
        url = gterm.URL + "/" + path
        target = "_blank" if url.endswith("/new") else path
        gterm.open_url(url, target=target)
        return

    if options.noauth:
        auth_code = "none"
        port = None
    else:
        auth_code, port = gterm.read_auth_code(user=options.user, server=options.server)

    Http_addr = options.server or "localhost"
    Http_port = options.port or port or gterm.DEFAULT_HTTP_PORT

    client_nonce = "1%018d" % random.randrange(0, 10**18)   # 1 prefix to keep leading zeros when stringified

    resp = auth_request(Http_addr, Http_port, client_nonce, user=options.user, protocol=protocol)
    if not resp:
        print >> sys.stderr, "\ngterm: Authentication request to GraphTerm server %s:%s failed" % (Http_addr, Http_port)
        print >> sys.stderr, "gterm: Server may not be running; use 'gtermserver' command to start it."
        sys.exit(1)

    server_nonce, received_token = resp.split(":")
    client_token, server_token = auth_token(auth_code, "graphterm", client_nonce, server_nonce)
    if received_token != client_token:
        print >> sys.stderr, "gterm: GraphTerm server %s:%s failed to authenticate itself (Check port number, if necessary)" % (Http_addr, Http_port)
        sys.exit(1)

    ##print >> sys.stderr, "**********snonce", server_nonce, client_token, server_token

    # Open graphterm window using browser
    url = "%s://%s:%d" % (protocol, Http_addr, Http_port)
    if path:
        url += "/" + path
    code = gterm.compute_hmac(auth_code, server_nonce)
    url += "/?cauth="+server_nonce+"&code="+code
    if options.user:
        url += "&user="+options.user

    std_out, std_err = gterm.open_browser(url, browser=options.browser)
    if std_err:
        print >> sys.stderr, "gterm: ERROR in opening browser window '%s' - %s\n Check if server is running. If not, start it with 'gtermserver' command." % (" ".join(command_args), std_err)
        sys.exit(1)

    # TODO: Create minimal browser window (without URL box etc.)
    # by searching directly for browser executables, or using open, xdg-open, or gnome-open
    # For security, closing websocket should close out (or at least about:blank) the terminal window
    # (to prevent reconnecting to malicious server)

if __name__ == "__main__":
    main()
