import { useState } from "react";
import { Link } from "react-router-dom";
import AuthCard from "../../../components/common/AuthCard";
import { ROUTES } from "../../../app/paths";
import { authApi } from "../../../services/authApi";

export default function RegisterPage() {
  const [form, setForm] = useState({
    company_name: "",
    company_url: "",
    contact_email: "",
    about_company: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const onChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsSubmitting(true);

    try {
      const data = await authApi.registerCompany(form);
      setMessage(data.message || "Company registered successfully.");
      setForm({
        company_name: "",
        company_url: "",
        contact_email: "",
        about_company: "",
      });
    } catch (requestError) {
      setError(requestError.message || "Unable to register company.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthCard
      title="Register your company"
      subtitle="Create workspace and approve your company domain."
    >
      <form className="form" onSubmit={onSubmit}>
        <label>
          Company name
          <input name="company_name" value={form.company_name} onChange={onChange} required />
        </label>
        <label>
          Company website
          <input
            name="company_url"
            placeholder="https://www.amazon.com"
            value={form.company_url}
            onChange={onChange}
            required
          />
        </label>
        <label>
          Contact email
          <input
            type="email"
            name="contact_email"
            placeholder="admin@amazon.com"
            value={form.contact_email}
            onChange={onChange}
            required
          />
        </label>
        <label>
          About company (optional)
          <textarea name="about_company" rows={3} value={form.about_company} onChange={onChange} />
        </label>

        {message ? <div className="alert success">{message}</div> : null}
        {error ? <div className="alert error">{error}</div> : null}

        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Registering..." : "Register Company"}
        </button>
      </form>

      <p className="route-cta">
        Already registered? <Link to={ROUTES.login} style={{ color: '#8219a2' }}>Request magic link</Link>
      </p>
    </AuthCard>
  );
}
