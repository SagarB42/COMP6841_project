import sqlite3
import requests
from flask import Flask, request, session, redirect, url_for, g, flash, render_template, abort
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_COOKIE_HTTPONLY'] = True
DATABASE = 'database.db'

def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect(DATABASE)
        g.sqlite_db.row_factory = sqlite3.Row
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    init_db()
    print('Initialized the database.')

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        query = "SELECT * FROM users WHERE username = ? AND password = ?"
        user = db.execute(query, (username, password)).fetchone()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('home'))
        else:
            error = 'Invalid username or password. Please try again.'

    if 'user_id' in session:
        return redirect(url_for('home'))
        
    return render_template('index.html', error=error)

@app.route('/register', methods=['POST'])
def register():
    error = None
    username = request.form['username']
    password = request.form['password']
    retype_password = request.form['retype_password']

    if not username or not password or not retype_password:
        error = "All fields are required."
    elif password != retype_password:
        error = "Passwords do not match."
    else:
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                       [username, password, 'user'])
            db.commit()
            flash('You were successfully registered! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = f"User {username} is already registered."
    
    flash(error, 'error')
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    search_query = request.args.get('search', '')
    user_id = session['user_id']

    if session.get('role') == 'admin':
        my_posts_query = 'SELECT p.id, p.title, p.content, p.timestamp, p.visibility, p.author_id, u.username as author FROM posts p JOIN users u ON p.author_id = u.id ORDER BY p.timestamp DESC'
        my_posts = db.execute(my_posts_query).fetchall()
    else:
        my_posts_query = 'SELECT p.id, p.title, p.content, p.timestamp, p.visibility, p.author_id, u.username as author FROM posts p JOIN users u ON p.author_id = u.id WHERE p.author_id = ? ORDER BY p.timestamp DESC'
        my_posts = db.execute(my_posts_query, (user_id,)).fetchall()

    if search_query:
        query = "SELECT p.id, p.title, p.content, p.timestamp, p.author_id, u.username as author FROM posts p JOIN users u ON p.author_id = u.id WHERE p.visibility = 'public' AND p.title LIKE ? ORDER BY p.timestamp DESC"
        public_posts = db.execute(query, ('%' + search_query + '%',)).fetchall()
    else:
        query = "SELECT p.id, p.title, p.content, p.timestamp, p.author_id, u.username as author FROM posts p JOIN users u ON p.author_id = u.id WHERE p.visibility = 'public' ORDER BY p.timestamp DESC"
        public_posts = db.execute(query).fetchall()
    
    return render_template('home.html', 
                           my_posts=my_posts, 
                           public_posts=public_posts, 
                           username=session['username'],
                           is_admin=(session.get('role') == 'admin'),
                           search_query=search_query)

@app.route('/post/<int:post_id>')
def post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    post_data = db.execute('SELECT p.id, p.title, p.content, p.timestamp, p.visibility, p.author_id, u.username as author FROM posts p JOIN users u ON p.author_id = u.id WHERE p.id = ?', [post_id]).fetchone()
    
    if post_data is None:
        abort(404)
        
    if post_data['visibility'] == 'private' and post_data['author_id'] != session['user_id'] and session.get('role') != 'admin':
        flash('This post is private.', 'error')
        return redirect(url_for('home'))
        
    return render_template('post.html', post=post_data)

@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        visibility = request.form.get('visibility', 'public')
        author_id = session['user_id']
        
        db = get_db()
        db.execute('INSERT INTO posts (title, content, author_id, visibility) VALUES (?, ?, ?, ?)', [title, content, author_id, visibility])
        db.commit()
        return redirect(url_for('home'))
        
    return render_template('new_post.html')

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    post_data = db.execute('SELECT * FROM posts WHERE id = ?', [post_id]).fetchone()

    if post_data is None:
        abort(404)
        
    if post_data['author_id'] != session['user_id'] and session.get('role') != 'admin':
        abort(403)
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        visibility = request.form.get('visibility', 'public')
        db.execute('UPDATE posts SET title = ?, content = ?, visibility = ? WHERE id = ?', [title, content, visibility, post_id])
        db.commit()
        return redirect(url_for('post', post_id=post_id))

    return render_template('edit_post.html', post=post_data)

@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    post_data = db.execute('SELECT author_id FROM posts WHERE id = ?', [post_id]).fetchone()

    if post_data is None:
        abort(404)
    
    if post_data['author_id'] != session['user_id'] and session.get('role') != 'admin':
        abort(403)
        
    db.execute('DELETE FROM posts WHERE id = ?', [post_id])
    db.commit()
    flash('Post deleted successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if user_id != session['user_id'] and session.get('role') != 'admin':
        abort(403)

    db = get_db()
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        profile_pic_url = request.form.get('profile_pic_url')
        
        query = "UPDATE users SET first_name = ?, last_name = ? WHERE id = ?"
        db.execute(query, (first_name, last_name, user_id))
        db.commit()

        if profile_pic_url:
            try:
                if not profile_pic_url.startswith(('http://', 'https://')):
                    raise requests.RequestException("Invalid URL scheme.")

                response = requests.get(profile_pic_url, timeout=5)
                content_type = response.headers.get('Content-Type', '')

                if response.status_code == 200 and 'image' in content_type:
                    db.execute('UPDATE users SET profile_pic_url = ? WHERE id = ?', [profile_pic_url, user_id])
                    db.commit()
                    flash('Profile picture updated!', 'success')
                else:
                    flash("URL did not point to a valid image.", "danger")

            except requests.RequestException as e:
                flash(f"Could not fetch data from URL: {e}", "error")
        
        if not profile_pic_url:
             flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile', user_id=user_id))
    
    user_profile = db.execute('SELECT id, username, first_name, last_name, profile_pic_url FROM users WHERE id = ?', [user_id]).fetchone()
    if user_profile is None:
        abort(404)
        
    return render_template('profile.html', user=user_profile)

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if session.get('role') != 'admin':
        abort(403) 
    
    db = get_db()
    users = db.execute('SELECT id, username, role, first_name, last_name FROM users').fetchall()
    return render_template('admin.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('role') != 'admin':
        abort(403)

    if session.get('user_id') == user_id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('admin'))
    
    db = get_db()
    db.execute('DELETE FROM posts WHERE author_id = ?', (user_id,))
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()

    flash(f"User (ID: {user_id}) and all their posts have been deleted.", "success")
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

