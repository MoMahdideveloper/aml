import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, url_for

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
    agents = database_service.get_agents()
    return render_template(
        "customers.html",
        customers=customers,
        agents=agents,
        agents_list=agents,
    )


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


@bp.route("/api/customers/<int:customer_id>")
def get_customer_json(customer_id):
    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        return jsonify({"error": "Customer not found"}), 404
    return jsonify(customer.to_dict())


@bp.route("/customers/<int:customer_id>/edit", methods=["POST"])
def edit_customer(customer_id):
    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        flash("Customer not found.", "error")
        return redirect(url_for("customers"))

    form = CustomerForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("customers"))

    try:
        from sqlalchemy_models import Customer
        existing = Customer.query.filter(
            Customer.email == form.email.data, Customer.id != customer_id
        ).first()
        if existing:
            flash(f"Email {form.email.data} is already in use by another customer.", "error")
            return redirect(url_for("customers"))

        database_service.update_customer(
            customer_id,
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            budget_min=float(form.budget_min.data or 0),
            budget_max=float(form.budget_max.data or 0),
            preferred_bedrooms=int(form.preferred_bedrooms.data or 0),
            preferred_bathrooms=int(form.preferred_bathrooms.data or 0),
            preferred_type=form.preferred_type.data or "",
            location_preference=form.location_preference.data or "",
        )
        flash(f'Customer "{form.name.data}" updated successfully!', "success")
    except Exception as e:
        logging.exception("Error updating customer")
        flash(f"Error updating customer: {str(e)}", "error")
    return redirect(url_for("customers"))


@bp.route("/customers/<int:customer_id>/delete", methods=["POST"])
def delete_customer(customer_id):
    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        flash("Customer not found.", "error")
        return redirect(url_for("customers"))

    active_deals = [d for d in customer.deals if d.status not in ["closed_won", "closed_lost"] and not getattr(d, "is_deleted", False)]
    if active_deals:
        flash(f"Cannot delete customer '{customer.name}' because they have active deals.", "error")
        return redirect(url_for("customers"))

    try:
        database_service.delete_customer(customer_id)
        flash(f"Customer '{customer.name}' deleted successfully!", "success")
    except Exception as e:
        logging.exception("Error deleting customer")
        flash(f"Error deleting customer: {str(e)}", "error")
    return redirect(url_for("customers"))
