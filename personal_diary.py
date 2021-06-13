from os import name
from flask import Flask, request, render_template, session, url_for, redirect, flash
from pymongo import MongoClient
import time
from wtforms import Form,StringField, TextField, PasswordField, validators
import gridfs
from bson.objectid import ObjectId
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired

class RegistrationForm(Form):
    username = TextField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')

class DiaryForm(FlaskForm):
    title = StringField('title',validators=[DataRequired()])
    post_time = StringField('post_time',validators=[DataRequired()])
    contents = StringField('contents',validators=[DataRequired()])

myclient = MongoClient('mongodb://localhost:27017/')
mydb = myclient["personal_diary"]
user_collection = mydb["userinfo"]

app = Flask(__name__)
app.secret_key = 'Software Engineering'
app.config['SESSION_TYPE'] = 'filesystem'
 
@app.route("/")
def home():
    if ("logged_in" in session and session["logged_in"] == True):
        return redirect(url_for('board',username = session["current_user"]))
    
    return redirect(url_for('login'))
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        
            #DB에 일치하는 아이디 비밀번호 확인
            #해당 유저의 DB로 들어가서 게시글 확인하기
        if (user_collection.find_one({"name":username})):
            id_matched = user_collection.find_one({"name": username})
            if(id_matched["password"] == password):
                session["logged_in"] = True
                session["current_user"] = username
                return redirect(url_for('board', username = username))            
            else:
                flash("Wrong Password.")
                return render_template('login.html')
        else:
            flash("User does not exist.")
            return render_template('login.html')
    else:
        return render_template('login.html')
 
 
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if (request.method == 'POST' and form.validate()):
        if (user_collection.find_one({"name":request.form['username']})):
            flash("There is same user already.")
            return render_template("register.html", form= form)
        else:    
            username = request.form['username']
            password = request.form['password']
            new_user = {"name" : username, "password" : password}
            user_collection.insert_one(new_user)
            flash("Register Success.")
            return redirect(url_for('login'))
    else:
        return render_template('register.html', form = form)
 
 
@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for("home"))


@app.route("/post", methods=["GET", "POST"])
def post():
    # 게시글 양식 정해주기
    if request.method == 'POST':
        uploader_name = session["current_user"]
        post_time = time.strftime("%Y%m%d_%H%M%S")
        title = request.form.get("title")
        contents = request.form.get("contents")
        fs = gridfs.GridFS(mydb, uploader_name)
        fileID = fs.put(request.files["file"])
        new_post = {
            "title" : title,
            "uploader" : uploader_name,
            "contents" : contents,
            "post_time" : post_time,
        }
        
        mydb[uploader_name].insert_one(new_post)
        return redirect(url_for('board', username = uploader_name))
    
    else:
        return render_template("post.html", username = session["current_user"])

@app.route("/board/<username>", methods = ["GET", "POST"])
def board(username):
    if(request.method == "GET" and session["logged_in"] == True and username == session["current_user"]):
        diary = mydb[username].find()
        file = mydb[username+".files"].find()
        return render_template("board.html" ,username = username, diary=diary, file = file)
    else:
        return "Error"

@app.route("/board/<username>/<id>", methods = ["GET"])
def postview(username, id):
    username = session["current_user"]
    diary = mydb[username].find_one({'_id':ObjectId(id)})
    
    if(diary):
        return render_template("postview.html", diary = diary, username = username)

    else:
        return "no diary here"

@app.route('/update/<id>', methods = ["GET", "POST"])
def updatepost(id):
    username = session["current_user"]
    diary = mydb[username].find_one({'_id':ObjectId(id)})
    form = DiaryForm()
    if form.validate_on_submit():
        new_title = request.form.get("title")
        new_post_time = request.form.get("post_time")
        new_contents = request.form.get("contents")

        mydb[username].update({'_id':ObjectId(id)}, {"title":new_title, "post_time":new_post_time,"contents":new_contents})
        return redirect(url_for('update.html',diary =  diary, username = username, form = form))
    
    else:
        return render_template('update.html',diary =  diary, username = username, form=form)

@app.route('/delete/<id>')
def deletepost(id):
    username = session["current_user"]
    mydb[username].remove({"_id":ObjectId(id)})
    return redirect(url_for('board', username = username))

if __name__ == '__main__':
    app.run(debug= True)