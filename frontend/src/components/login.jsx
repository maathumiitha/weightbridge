import "../styles/login.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = (event) => {
    event.preventDefault();
    setError("");

    if (!formData.email.trim() || !formData.password.trim()) {
      setError("Email and password are required.");
      return;
    }

    setIsSubmitting(true);
    window.setTimeout(() => {
      setIsSubmitting(false);
      navigate("/weighment");
    }, 650);
  };

  return (
    <section className="login-page">
      <div className="login-ambient login-ambient-left" />
      <div className="login-ambient login-ambient-right" />

      <form className="form" onSubmit={onSubmit}>
        <header className="login-copy">
          <h1>Login</h1>
          <p className="login-subtitle">Secure access for weighbridge operations.</p>
        </header>

        <div className={`shine-card${error ? " is-invalid" : ""}`}>
          <span className="input-span">
            <label htmlFor="email" className="label">
              Email
            </label>
            <input
              type="email"
              name="email"
              id="email"
              placeholder="Enter your email"
              value={formData.email}
              onChange={(event) =>
                setFormData((current) => ({ ...current, email: event.target.value }))
              }
            />
          </span>

          <span className="input-span">
            <label htmlFor="password" className="label">
              Password
            </label>
            <input
              type="password"
              name="password"
              id="password"
              placeholder="Enter your password"
              value={formData.password}
              onChange={(event) =>
                setFormData((current) => ({ ...current, password: event.target.value }))
              }
            />
          </span>

          {error ? <p className="login-error">{error}</p> : null}

          <button className="submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Log in"}
          </button>
        </div>

        <span className="span">
          <a href="#">Forgot password?</a>
        </span>
      </form>
    </section>
  );
}
