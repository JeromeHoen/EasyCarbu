from flask import Flask, render_template, request
from results import get_results


app = Flask(__name__)

@app.route('/home/', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return get_results(
            input_url = request.form['maps_url'],
            gas = request.form['gas'],
            consumption_per_100km = float(request.form['consumption']),
            liters_to_fill_up = float(request.form['liters']),
            trade_off = float(request.form['trade_off']),
            km_start = float(request.form['start']),
            km_end = float(request.form['end'])
        )
    return render_template("home.html")

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        return "Vous avez envoyé : {msg}".format(msg=request.form['msg'])
    return """<form action="" method="post"><input type="text" name="msg" /><input type="submit" value="Envoyer" /></form>"""

if __name__ == "__main__":
    app.run(debug=True)