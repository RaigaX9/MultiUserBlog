import string
import webapp2
import os
import jinja2
import re
import hashlib
import hmac
import random
import json

from google.appengine.ext import db

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(
        os.path.dirname(__file__), 'templates')), autoescape=True)


# This will provide the main functions for the blog when users are logged in.


class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.fromuserId(int(uid))

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def read_secure_cookie(self, name):
        x = self.request.cookies.get(name)
        return x and verifysecurestr(x)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        x = securestr(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, x))

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')


# Allows users to register and login based on their username and password.


class User(db.Model):
    name = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)

    @classmethod
    def register(cls, name, pw):
        pw_hash = hashfunc(name, pw)
        return User(parent=uk(),
                    name=name,
                    pw_hash=pw_hash)

    @classmethod
    def fromuserId(cls, uid):
        return User.get_by_id(uid, parent=uk())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and hashpass(name, pw, u.pw_hash):
            return u


# This will allow the user to sign up for with certain
# validations for username, password, and verify them.
class Signup(BlogHandler):
    def get(self):
        self.render("register.html", page_type="login")

    def post(self):
        self.username = self.request.get("username")
        self.password = self.request.get("password")
        self.verify = self.request.get("verify")

        params = dict(username=self.username)
        have_error = False

        un = User.by_name(self.username)
        if un:
            params['usernameerror'] = "Username already exists"
            have_error = True

        if not userValid(self.username):
            params['usernameerror'] = "Username is not valid"
            have_error = True

        if not passValid(self.password):
            params['passworderror'] = "Password is not valid"
            have_error = True
        else:
            if self.password != self.verify:
                params['verifyerror'] = "Both passwords don't match"
                have_error = True

        # redraw the signup page if user input is invalid
        if have_error:
            params['page_type'] = "login"
            self.render("register.html", **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError


# Create blog post from a user
class Post(db.Model):
    username = db.StringProperty(required=True)
    subject = db.TextProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    permalink = db.StringProperty()

    @classmethod
    def fromuserId(cls, pid):
        return Post.get_by_id(pid)


# Create comment from a user
class Comment(db.Model):
    username = db.StringProperty(required=True)
    comment = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    pid = db.StringProperty(required=True)

    @classmethod
    def fromuserId(cls, cid):
        return Comment.get_by_id(cid)

    @classmethod
    def fromuserPost(cls, pid):
        return Comment.all().filter('pid =', str(pid)).order('-created')


# Completes registration
class Register(Signup):
    def done(self):
        u = User.register(self.username, self.password)
        u.put()
        self.login(u)
        self.redirect('/home')


# Allows the user to be logged in  and returns to the home page.
class Login(BlogHandler):
    def get(self):
        self.render("login.html", page_type="login")

    def post(self):
        self.username = self.request.get("username")
        self.password = self.request.get("password")
        correctlogin = User.login(self.username, self.password)
        if correctlogin:
            self.login(correctlogin)
            self.redirect('/home')
        else:
            self.render(
                "login.html", page_type="login", messageerror="Invalid login."
                "Either you username or password is wrong.")


# Logs out the user.
class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/login')


# Retrieves blog post and place it in the home page.
class Blog(BlogHandler):
    def get(self):
        posts = Post.all().order('-created')
        if self.user:
            self.render("home.html", username=self.user.name, posts=posts)
        else:
            self.render("home.html", posts=posts)


# This will create a new post for those who are logged in.
class CreatePost(BlogHandler):
    def get(self):
        if self.user:
            self.render("createpost.html", username=self.user.name)
        else:
            self.redirect('/login')

    def post(self):
        self.username = self.request.get("username")
        self.subject = self.request.get("subject")
        self.content = self.request.get("content")

        if self.user:
            if self.subject and self.content:
                p = Post(username=self.username,
                         subject=self.subject, content=self.content)
                p.put()
                p_key = p.key().id()
                p.permalink = str(p_key)
                p.put()
                self.redirect("/thread/%s" % p_key)
            else:
                self.render("createpost.html", username=self.username,
                            messageerror="Title and Description are required.")
        else:
            self.write("Login is required to post")


# This will view the blog post.
class ViewPost(BlogHandler):
    def get(self, pid):
        post = Post.get_by_id(int(pid))
        if post:
            comments = Comment.fromuserPost(pid)
            params = dict(post=post, comments=comments)
            if self.user:
                params['username'] = self.user.name
                self.render("viewpost.html", **params)
            else:
                self.render("viewpost.html", **params)


# This will allow the user to edit their blog post.
class PostEdit(BlogHandler):
    def post(self):
        if self.user:
            pid = self.request.get("pid")
            subject = self.request.get("subject")
            content = self.request.get("content")

            if subject and content:
                p = Post.fromuserId(int(pid))
                p.subject = subject
                p.content = content

                if self.user.name == p.username:
                    p.put()
                    self.response.out.write(json.dumps(
                        ({'message': "Post Edit Changed!"})))
                else:
                    self.response.out.write(json.dumps(
                        ({'error': "ERROR: You can't edit others' post."})))
            else:
                self.response.out.write(json.dumps(
                    ({'error': "Title and description are both required!"})))
        else:
            self.response.out.write(json.dumps(
                ({'error': "Login is required"})))


# This will allow the user to delete blog post.
class PostDelete(BlogHandler):
    def post(self):
        if self.user:
            pid = self.request.get("pid")
            thepost = Post.fromuserId(int(pid))
            thepost.delete()

            if self.user.name == thepost.username:
                self.response.out.write(json.dumps(
                    ({'message': "Post Deleted."})))


# Posts user comment
class UserComment(BlogHandler):
    def post(self):
        ucomment = self.request.get("usercomment")
        thecom = Comment.fromuserId(int(ucomment))
        self.response.out.write(json.dumps(
            ({'comment': thecom.comment})))


# Comment section where users can post comments
class CommentSection(BlogHandler):
    def post(self):
        thecom = self.request.get("comment")
        pid = self.request.get("pid")

        if self.user:
            if thecom:
                com = Comment(username=self.user.name,
                              comment=thecom, pid=pid)
                com.put()
            else:
                self.response.out.write(json.dumps(
                    ({'error': "Comment is required"})))
        else:
            self.response.out.write(json.dumps(
                ({'error': "Login is required to comment"})))
# Allows user to edit their comments.


class EditComment(BlogHandler):
    def post(self):
        if self.user:
            usercomment = self.request.get("usercomment")
            comment = self.request.get("comment")
            if comment:
                c = Comment.fromuserId(int(usercomment))
                if c.username == self.user.name:
                    c.comment = comment
                    c.put()
                    self.response.out.write(json.dumps(
                        ({'message': "Comment Edited"})))


# Allows the users to delete their comments.
class DeleteComment(BlogHandler):
    def post(self):
        if self.user:
            usercomment = self.request.get("usercomment")
            c = Comment.fromuserId(int(usercomment))

            if c.username == self.user.name:
                c.delete()
                self.response.out.write(json.dumps(
                    ({'message': "Comment deleted"})))


# Creates random texts for hashing
def randomtext():
    i, j = '', len(string.letters) - 1
    for _ in range(5):
        i = i + string.letters[random.randint(0, j)]
    return i


# Hash Function
def hashfunc(name, pw, r=None):
    if not r:
        r = randomtext()
    hash1 = hashlib.sha256(name + pw + r).hexdigest()
    return '%s,%s' % (hash1, r)


# Hashes on passwords
def hashpass(name, pw, hp):
    r = hp.split(",")[1]
    x = hashfunc(name, pw, r)
    return hp == x


# Validates proper username
def userValid(username):
    regex = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return regex.match(username) and username


# Validates two passwords
def passValid(password):
    regex = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return regex.match(password) and password


# Checks to see if securestr are the same
def verifysecurestr(n2):
    x = n2.split('|')[0]
    if n2 == securestr(x):
        return x


# Creates a secure string
def securestr(n):
    return '%s|%s' % (n, hmac.new("PLeaSEMakEThiSSECuRE", n).hexdigest())


# Returns user keys
def uk(a='default'):
    return db.Key.from_path('users', a)


# Returns post keys
def pk(a='default'):
    return db.Key.from_path('posts', a)


app = webapp2.WSGIApplication([
    ('', Blog),
    ('/', Blog),
    ('/home', Blog),
    ('/register', Register),
    ('/login', Login),
    ('/logout', Logout),
    ('/createpost', CreatePost),
    ('/thread/(\d+)', ViewPost),
    ('/editcomment', EditComment),
    ('/usercomment', UserComment),
    ('/postedit', PostEdit),
    ('/delete', PostDelete),
    ('/comment', CommentSection),
    ('/deletecomment', DeleteComment)
], debug=True)
