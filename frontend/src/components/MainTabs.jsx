import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Master", to: "/master" },
  { label: "Weighment", to: "/weighment" },
  { label: "Sms", to: "/sms" },
  { label: "Reports", to: "/reports" },
  { label: "Live View", to: "/live-view" },
];

export default function MainTabs() {
  return (
    <nav className="wm-nav">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => `wm-nav-btn${isActive ? " active" : ""}`}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
