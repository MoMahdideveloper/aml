import logging
from flask import Blueprint, render_template, redirect, url_for, flash

from database_service import database_service
from forms import CustomerForm


bp = Blueprint("customers", __name__)


@bp.route("/customers")
def customers():
    customers = database_service.get_customers()
    for customer in customers:
        setattr(customer, "total_deals", len(customer.deals))
        setattr(
            customer,
            "active_deals",
            len([d for d in customer.deals if d.status not in ["closed_won", "closed_lost"]]),
        )
    return render_template("customers.html", customers=customers)


@bp.route("/customers/add", methods=["POST"])
def add_customer():
    form = CustomerForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("customers"))
    try:
        database_service.add_customer(
            form.name.data,
            form.email.data,
            form.phone.data,
            float(form.budget_min.data or 0),
            float(form.budget_max.data or 0),
            int(form.preferred_bedrooms.data or 0),
            int(form.preferred_bathrooms.data or 0),
            form.preferred_type.data or "",
            form.location_preference.data or "",
        )
        flash(f'Customer "{form.name.data}" added successfully!', "success")
    except Exception as e:
        logging.exception("Error adding customer")
        flash(f"Error adding customer: {str(e)}", "error")
    return redirect(url_for("customers"))
