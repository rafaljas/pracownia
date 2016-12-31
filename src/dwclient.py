# -*- coding: cp1250 -*-
# created: 2007-12-06 09:51:59
# filename: dw_handler

# place for file global imports and defines
import urllib, urllib2, cookielib, re, string, time

# some place for code
class wikiclient:
        def __init__(self, path, user, password):
                self.path = path + 'doku.php'
                self.user = user
                self.passwd = password
                self.loggedin = False
                self.last_error = False

                self.cj = cookielib.CookieJar()
                self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))

        def __get_url_content(self, query = ''):
                query_url = urllib.urlencode(query)
                query_response = self.opener.open(self.path, query_url).readlines()
                return query_response
                try:
                        query_response = self.opener.open(self.path, query_url).readlines()
                except Exception, e:
                        self.last_error = e
                        raise e
                        return ''
                return query_response

        # login / logout
        def is_loggedin(self, page_html = ''):
                if not page_html:
                        query = []
                        response = self.__get_url_content(query)
                        page_html = ''.join(response)
                return ('<div class="cuinfo">' in page_html) and not ('<div class="cuinfo"></div>' in page_html)

        def log_in(self):
                self.cj.clear()
                
                # dokuwiki page http query parameters
                user = ('u', self.user)
                passwd = ('p', self.passwd)
                action = ('do', 'login')

                query = [action, user, passwd]
                response = self.__get_url_content(query)
                page_html = ''.join(response)

                if self.is_loggedin():
                        self.loggedin = True
                        return True

                return False
        
        def log_out(self):
                self.cj.clear()
                # dokuwiki page http query parameters
                action = ('do', 'login')

                query = [action]
                response = self.__get_url_content(query)
                page_html = ''.join(response)

                if not self.is_loggedin():
                        self.loggedin = False
                        return True

                return False

        # pages operations
        def page_get(self, page_id = '', page_rev = ''):
                # dokuwiki page http query parameters
                id = ('id', page_id)
                rev = ('rev', page_rev)

                query = [id, rev]
                response = self.__get_url_content(query)
                page_html = ''.join(response)

                return page_html

        def page_get_txt(self, page_id = '', page_rev = ''):
                # non blocking access to page txt source - logout, read, login again
                self.log_out()
                # dokuwiki page http query parameters
                id = ('id', page_id)
                rev = ('rev', page_rev)
                action = ('do', 'edit')

                query = [id, rev, action]
                response = self.__get_url_content(query)
                
                self.log_in()

                page_html = ''
                do_copy = False
                #print "dwclient>>> get_page:\n", response, "\n<<<dwclient"
                for line in response:
                        if line.find('<textarea name="wikitext"') + 1:
                                do_copy = True

                        if do_copy:
                                page_html += line

                        if line.find('</textarea>') + 1:
                                do_copy = False

                page_html = re.sub('.*name="wikitext"', '', page_html)
                page_html = re.sub('</textarea>.*', '', page_html)
                page_html = re.sub('.*>', '', page_html)

                return page_html

        def page_save(self, page_id , page_content, page_summary = 'aktualizacja systemowa'):
                if not self.loggedin:
                        self.log_in()

                now = str(time.time())
                if page_content:
                       page_content = "".join(["<html><!--aktualizacja:", now, "--></html>", page_content])
                #print "dwclient>>> page content:\n", page_content, "\n<<<dwclient"
                # dokuwiki page http query parameters
                id = ('id', page_id)
                summary = ('summary', page_summary)
                wikitext = ('wikitext', page_content)
                action = ('do', 'save')

                query = [id, summary, wikitext, action]
                response = self.__get_url_content(query)

                check_save_response = self.page_get_txt(page_id)
                #print "dwclient>>> response:\n", check_save_response, "\n<<<dwclient"
                
                if page_content:
                        return "!--aktualizacja:"+now+"--" in check_save_response
                else:
                        return check_save_response == ''

        def page_del(self, page_id):
                return self.page_save(page_id, '')

#{{{ python version check
if __name__ == '__main__':
        from sys import version_info, exit, stderr

        ver = (2,5)
        if ver > version_info[:2]:
                stderr.write("Python is too old, please clean up the molt and rejuvenate to version %d.%d.\n" % ver)
                exit(1)

        w =wikiclient("http://localhost:8800/", "wiki123", "123qwe")
        print urllib2.urlopen("http://www.google.pl/").read(100)
        print urllib2.urlopen("http://localhost:8800/doku.php").read(100)
        w.log_in()
        #}}}

