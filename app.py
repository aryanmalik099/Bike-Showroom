from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from dotenv import load_dotenv
from flask_mysqldb import MySQL
from datetime import datetime

app = Flask(__name__)

load_dotenv()
app.config['MYSQL_HOST'] = os.environ.get('DB_HOST')
app.config['MYSQL_USER'] = os.environ.get('DB_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('DB_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('DB_NAME')
app.config['MYSQL_PORT'] = int(os.environ.get('DB_PORT', '24396')) 

mysql = MySQL(app)
app.secret_key = os.environ.get('SECRET_KEY')


# Customer Home Page
@app.route('/', methods = ['GET', 'POST'])
def home():
    if request.method == 'POST':
        if session.get('loggedin')==None:
            return redirect(url_for('login'))
        bike_id = request.form['bike_id']
        session['bike_id'] = bike_id
        return render_template('buy.html')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM bikes where deleted=FALSE")
    bikes = cur.fetchall()
    cur.close()
    return render_template('customer.html', bikes=bikes)

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg=''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM cu_login WHERE username = %s AND password = %s", (username, password))
        cu = cur.fetchone()
        cur.close()

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM owners WHERE username = %s AND password = %s", (username, password))
        owner = cur.fetchone()
        cur.close()
        if cu:
            session['user'] = 'customer'
            session['loggedin'] = True
            session['id'] = cu[0]
            session['username'] = cu[1]
            return redirect(url_for('home'))
        elif owner:
            session['user'] = 'owner'
            session['loggedin'] = True
            session['id'] = owner[0]
            session['username'] = owner[1]
            return redirect(url_for('owner'))
        else:
            msg = 'Invalid Credentials!'
    return render_template('login.html',msg=msg)


# Registeration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg='CREATE AN ACCOUNT'
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM cu_login WHERE username = %s or email = %s", (username,email,))
        account = cur.fetchone()
        if account:
            msg = 'Account already exists!'
        else:
            cur.execute("INSERT INTO cu_login(username,email,password) VALUES(%s, %s, %s)", (username, email, password))
            mysql.connection.commit()
            cur.close()
            msg = 'You have successfully registered!'
            return render_template('login.html', msg=msg)
    return render_template('register.html', msg=msg)


# Logout
@app.route('/logout')
def logout():
    if session.get('user') == 'customer':
        session.pop('user', None)
        session.pop('loggedin', None)
        session.pop('id', None)
        session.pop('username', None)
    else:
        session.pop('user', None)
        session.pop('loggedin', None)
        session.pop('id', None)
        session.pop('username', None)
    return redirect(url_for('home'))


# Buy Page
@app.route('/buy', methods=['GET', 'POST'])
def buy():
    msg = ''
    id = session.get('id')
    

    if session.get('loggedin')==None:
        return redirect(url_for('login'))
    else:
        if request.method == 'POST':
            bike_id = session.get('bike_id')
            name = request.form['name']
            contact_no = request.form['contact_no']
            email = request.form['email']
            address = request.form['address']
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            main = 'home'
            if session.get('user') == 'customer':
                main = 'home'
            elif session.get('user') == 'owner':
                main = 'owner'

            try:
                cur = mysql.connection.cursor()
                cur.execute("SELECT * FROM bikes WHERE bike_id = %s", (bike_id,))
                bike = cur.fetchone()
                price = bike[4]
                cur.execute("INSERT INTO customers (name, contact_no, email, address, date, bike_id) VALUES (%s, %s, %s, %s, %s, %s)", (name, contact_no, email, address, date, bike_id))
                cur.execute("INSERT INTO sales (bike_id, customer_id, sale_date, sale_price) VALUES (%s, LAST_INSERT_ID(), %s, %s)", (bike_id, date, price))
                cur.execute("UPDATE bikes SET stock = stock - 1 WHERE bike_id = %s", (bike_id,))
                mysql.connection.commit()
                cur.close()
                flash('PURCHASE SUCCESSFUL! THANKS FOR CHOOSING US!')
                return redirect(url_for(f'{main}'))
            except Exception as e:
                msg = f"Your purchase could not be completed. TRY AGAIN!"
                mysql.connection.rollback()
                return render_template('buy.html', id=id, msg=msg)
        return render_template(f'{main}.html', id=id, msg=msg)


# History Page
@app.route('/history')
def history():
    if session.get('loggedin')==None:
        return redirect(url_for('login'))
    else:
        id = session.get('id')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM customers WHERE id = %s", (id,))
        customer = cur.fetchone()
        cur.execute("SELECT * FROM sales WHERE customer_id = %s", (id,))
        sales = cur.fetchall()
        cur.close()
        return render_template('history.html', customer=customer, sales=sales)
    

# Owner Page
@app.route('/owner', methods=['GET', 'POST'])
def owner():
    if session.get('loggedin')==None or session.get('user')!='owner':
        flash('You must be logged in as an owner to access this page.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        bike_id = request.form['bike_id']
        session['bike_id'] = bike_id
        return render_template('buy.html')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM bikes WHERE deleted=FALSE")
    bikes = cur.fetchall()
    cur.close()
    return render_template('owner.html', bikes=bikes)
        

# Delete Bike
@app.route('/remove_bike/<int:bike_id>', methods=['POST'])
def remove_bike(bike_id):
    if session.get('loggedin')==None or session.get('user')!='owner':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE bikes SET deleted=TRUE WHERE bike_id = %s", (bike_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('owner'))


# Edit Bike
@app.route('/edit_bike/<int:bike_id>', methods=['GET', 'POST'])
def edit_bike(bike_id):
    if session.get('loggedin')==None or session.get('user')!='owner':
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM bikes WHERE bike_id = %s", (bike_id,))
    bike = cur.fetchone()
    cur.close()

    if request.method == 'POST':
        make = request.form.get('make')
        model = request.form.get('model')
        year = request.form.get('year')
        price = request.form.get('price')
        stock = request.form.get('stock')
        
        try:
            year = int(year)
            price = float(price)
            stock = int(stock)
            
            cur = mysql.connection.cursor()
            cur.execute("UPDATE bikes SET make = %s, model = %s, year = %s, price = %s, stock = %s WHERE bike_id = %s", (make, model, year, price, stock, bike_id))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('owner'))
        except Exception as e:
            flash('Invalid input! Please check the data you entered.')
            return render_template('edit_bike.html', bike=bike)
    return render_template('edit_bike.html', bike=bike)

# Add Bike
@app.route('/add_bike', methods=['GET', 'POST'])
def add_bike():
    if session.get('loggedin')==None or session.get('user')!='owner':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        make = request.form.get('make')
        model = request.form.get('model')
        year = request.form.get('year')
        price = request.form.get('price')
        stock = request.form.get('stock')

        try:
            year = int(year)
            price = float(price)
            stock = int(stock)

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO bikes (make, model, year, price, stock) VALUES (%s, %s, %s, %s, %s)", (make, model, year, price, stock))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('owner'))
        except Exception as e:
            return render_template('add_bike.html')

    return render_template('add_bike.html')


# Sales
@app.route('/sales')
def sales():
    if session.get('loggedin')==None or session.get('user')!='owner':
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("select sales.sale_id,bikes.make,bikes.model,bikes.year,bikes.price,customers.name,customers.contact_no,customers.address,customers.date from bikes join customers on bikes.bike_id=customers.bike_id join sales on customers.customer_id=sales.customer_id order by customers.date desc;")
    sales = cur.fetchall()
    cur.close()  
    return render_template('sales.html', sales=sales)


# Delete Sale
@app.route('/delete_sale/<int:sale_id>', methods=['POST'])
def delete_sale(sale_id):
    if session.get('loggedin')==None or session.get('user')!='owner':
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT customer_id FROM sales WHERE sale_id = %s", (sale_id,))
    customer_id = cur.fetchone()[0]
    cur.execute("DELETE FROM sales WHERE sale_id = %s", (sale_id,))
    cur.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('sales'))

if __name__ == '__main__':
    app.run(debug=True)
