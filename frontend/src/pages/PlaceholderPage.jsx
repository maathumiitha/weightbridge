import MainTabs from "../components/MainTabs";
import "../styles/placeholder.css";
import "../styles/weighment.css";

export default function PlaceholderPage({ title, description }) {
  return (
    <section className="placeholder-page">
      <div className="wm-ambient wm-ambient-left" />
      <div className="wm-ambient wm-ambient-right" />

      <div className="placeholder-shell">
        <header className="wm-topbar wm-panel">
          <MainTabs />
          <div className="wm-status-strip">
            <span className="wm-pill wm-pill-live">Preview</span>
          </div>
        </header>

        <div className="placeholder-card wm-panel">
          <p className="placeholder-eyebrow">Screen scaffold</p>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </div>
    </section>
  );
}
