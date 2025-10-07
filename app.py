import os
from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from io import BytesIO
from playwright.async_api import async_playwright
import asyncio

# --- App Initialization & Configuration ---
app = Flask(__name__)

# --- DATABASE CONFIGURATION FOR MYSQL ---
# IMPORTANT: Make sure these values match your MySQL credentials.
DB_USER = "roi_user"
DB_PASS = "swee090104"  # The password you set
DB_HOST = "localhost"
DB_NAME = "roi_simulator"
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}'
# --- END OF MYSQL CONFIGURATION ---

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Internal Constants ---
TIME_SAVED_PER_INVOICE_MINS = 8 

# --- Database Model ---
class Scenario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scenario_name = db.Column(db.String(100), nullable=False, default="Untitled Scenario")
    monthly_invoice_volume = db.Column(db.Float)
    num_ap_staff = db.Column(db.Float)
    avg_hours_per_invoice = db.Column(db.Float)
    hourly_wage = db.Column(db.Float)
    error_rate_manual = db.Column(db.Float)
    error_cost = db.Column(db.Float)
    time_horizon_months = db.Column(db.Float)
    one_time_implementation_cost = db.Column(db.Float)
    monthly_savings = db.Column(db.Float)
    roi_percentage = db.Column(db.Float)
    payback_months = db.Column(db.Float)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# --- Core Calculation Logic ---
def calculate_roi(data):
    volume = float(data.get('monthly_invoice_volume', 0))
    wage = float(data.get('hourly_wage', 0))
    horizon = float(data.get('time_horizon_months', 0))
    impl_cost = float(data.get('one_time_implementation_cost', 0))
    
    labor_savings = (TIME_SAVED_PER_INVOICE_MINS / 60) * wage * volume
    monthly_savings = labor_savings

    if monthly_savings <= 0:
        return {
            "monthly_savings": 0, "cumulative_savings": -impl_cost,
            "payback_months": float('inf'), "roi_percentage": -100 if impl_cost > 0 else 0
        }

    cumulative_savings = monthly_savings * horizon
    net_savings = cumulative_savings - impl_cost
    payback_months = impl_cost / monthly_savings if impl_cost > 0 else 0
    roi_percentage = (net_savings / impl_cost) * 100 if impl_cost > 0 else float('inf')

    return {
        "monthly_savings": round(monthly_savings, 2),
        "cumulative_savings": round(cumulative_savings, 2),
        "payback_months": round(payback_months, 1),
        "roi_percentage": round(roi_percentage, 2)
    }

# --- API Endpoints ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.get_json()
    results = calculate_roi(data)
    return jsonify(results)

# --- UPDATED WITH DEBUGGING ---
@app.route('/scenarios', methods=['POST'])
def save_scenario():
    print("\n--- DEBUG: '/scenarios' endpoint hit. ---")
    try:
        data = request.get_json()
        inputs = data.get('inputs', {})
        results = data.get('results', {})
        
        print(f"--- DEBUG: Received scenario name: {inputs.get('scenario_name')} ---")

        new_scenario = Scenario(
            scenario_name=inputs.get('scenario_name', 'Untitled'),
            monthly_invoice_volume=inputs.get('monthly_invoice_volume'),
            num_ap_staff=inputs.get('num_ap_staff'),
            avg_hours_per_invoice=inputs.get('avg_hours_per_invoice'),
            hourly_wage=inputs.get('hourly_wage'),
            error_rate_manual=inputs.get('error_rate_manual'),
            error_cost=inputs.get('error_cost'),
            time_horizon_months=inputs.get('time_horizon_months'),
            one_time_implementation_cost=inputs.get('one_time_implementation_cost'),
            monthly_savings=results.get('monthly_savings'),
            roi_percentage=results.get('roi_percentage'),
            payback_months=results.get('payback_months')
        )
        
        print("--- DEBUG: Scenario object created. Attempting to add to session. ---")
        db.session.add(new_scenario)
        print("--- DEBUG: Added to session. Attempting to commit to database. ---")
        db.session.commit()
        print("--- DEBUG: Commit successful! ---")
        
        return jsonify(new_scenario.to_dict()), 201
    except Exception as e:
        # This will catch any error during the process and print it
        db.session.rollback() # Roll back the transaction on error
        print(f"\n---!!! DATABASE ERROR !!!---\n{e}\n---!!! END OF ERROR !!!---\n")
        return jsonify({"error": "Failed to save to database.", "message": str(e)}), 500

@app.route('/scenarios', methods=['GET'])
def get_scenarios():
    scenarios = Scenario.query.order_by(Scenario.id.desc()).all()
    return jsonify([s.to_dict() for s in scenarios])

@app.route('/scenarios/<int:id>', methods=['GET'])
def get_scenario_details(id):
    scenario = Scenario.query.get_or_404(id)
    return jsonify(scenario.to_dict())

@app.route('/report/generate', methods=['POST'])
async def generate_report():
    data = request.get_json()
    user_email = data.get('email', 'not_provided@example.com')
    
    print(f"--- Report generated for: {user_email} ---")
    
    html_out = render_template('report_template.html', data=data)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_out)
        pdf_bytes = await page.pdf(format='A4')
        await browser.close()
        
    return send_file(
        BytesIO(pdf_bytes),
        as_attachment=True,
        download_name='invoicing_roi_report.pdf',
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)

