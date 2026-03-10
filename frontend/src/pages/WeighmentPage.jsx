import { useEffect, useMemo, useState } from "react";
import MainTabs from "../components/MainTabs";
import {
  getCameraFeeds,
  getLiveWeight,
  getNextSerialNumber,
  saveWeighment,
} from "../services/weighmentService";
import "../styles/weighment.css";

const initialFormData = {
  truckNo: "",
  materialCode: "",
  customerCode: "",
  charges: "",
  mobile1: "",
  mobile2: "",
  mobile3: "",
  serialNo: "1",
  materialName: "",
  customerName: "",
  loadWt: "",
  emptyWt: "",
  nettWeight: "",
  withCamera: true,
};

const actionButtons = [
  { label: "SAVE", tone: "save", type: "submit" },
  { label: "CANCEL", tone: "cancel", type: "button" },
  { label: "DELETE", tone: "delete", type: "button" },
  { label: "SHOW", tone: "show", type: "button" },
  { label: "PRINT", tone: "print", type: "button" },
  { label: "RE-SEND SMS", tone: "re-send-sms", type: "button" },
  { label: "RE-PRINT", tone: "re-print", type: "button" },
  { label: "RE-SEND WHATSAPP", tone: "re-send-whatsapp", type: "button" },
];

export default function WeighmentPage() {
  const [now, setNow] = useState(new Date());
  const [formData, setFormData] = useState(initialFormData);
  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [liveWeight, setLiveWeight] = useState({ weight: 0, stable: false, source: "mock" });
  const [cameraFeeds, setCameraFeeds] = useState([]);

  const logDate = useMemo(() => now.toLocaleDateString("en-GB"), [now]);
  const formattedNow = useMemo(() => now.toLocaleString("en-IN"), [now]);
  const displayWeight = `${Number(liveWeight.weight || 0).toLocaleString("en-IN")} Kg`;

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      const [serialNo, feeds, weight] = await Promise.all([
        getNextSerialNumber(),
        getCameraFeeds(),
        getLiveWeight(),
      ]);

      if (!active) {
        return;
      }

      setFormData((current) => ({
        ...current,
        serialNo: String(serialNo),
        loadWt: weight.weight > 0 ? String(weight.weight) : current.loadWt,
      }));
      setCameraFeeds(feeds);
      setLiveWeight(weight);
    }

    bootstrap();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    const timer = window.setInterval(async () => {
      const weight = await getLiveWeight();
      if (!active) {
        return;
      }

      setLiveWeight(weight);
      setFormData((current) => ({
        ...current,
        loadWt: weight.weight > 0 ? String(weight.weight) : current.loadWt,
      }));
    }, 2200);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const load = Number(formData.loadWt || 0);
    const empty = Number(formData.emptyWt || 0);
    const net = load > 0 && empty >= 0 ? Math.max(load - empty, 0) : 0;

    setFormData((current) => {
      const nextNet = net ? String(net) : "";
      if (current.nettWeight === nextNet) {
        return current;
      }
      return { ...current, nettWeight: nextNet };
    });
  }, [formData.loadWt, formData.emptyWt]);

  function handleChange(field, value) {
    setFormData((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      if (!current[field]) {
        return current;
      }
      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  function validateForm() {
    const nextErrors = {};

    if (!formData.truckNo.trim()) nextErrors.truckNo = "Truck number is required.";
    if (!formData.materialName.trim()) nextErrors.materialName = "Material name is required.";
    if (!formData.customerName.trim()) nextErrors.customerName = "Customer name is required.";
    if (!formData.mobile1.trim()) nextErrors.mobile1 = "Primary mobile number is required.";

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaveMessage("");

    if (!validateForm()) {
      return;
    }

    setIsSaving(true);
    try {
      const payload = {
        truck_number: formData.truckNo,
        material_code: formData.materialCode,
        customer_code: formData.customerCode,
        material_name: formData.materialName,
        customer_name: formData.customerName,
        charges: formData.charges,
        mobile_1: formData.mobile1,
        mobile_2: formData.mobile2,
        mobile_3: formData.mobile3,
        serial_no: Number(formData.serialNo),
        load_weight: Number(formData.loadWt || 0),
        empty_weight: Number(formData.emptyWt || 0),
        net_weight: Number(formData.nettWeight || 0),
        captured_at: now.toISOString(),
        with_camera: formData.withCamera,
      };

      await saveWeighment(payload);
      setSaveMessage("Weighment saved successfully.");
    } catch (error) {
      setSaveMessage("Save failed. Check backend connectivity and retry.");
    } finally {
      setIsSaving(false);
    }
  }

  function handleAction(label) {
    if (label === "CANCEL") {
      setFormData((current) => ({
        ...initialFormData,
        serialNo: current.serialNo,
        withCamera: current.withCamera,
      }));
      setErrors({});
      setSaveMessage("");
    }
  }

  return (
    <section className="wm-page">
      <div className="wm-ambient wm-ambient-left" />
      <div className="wm-ambient wm-ambient-right" />

      <div className="wm-shell">
        <header className="wm-topbar wm-panel">
          <MainTabs />

          <div className="wm-status-strip">
            <span className="wm-pill wm-pill-live">{liveWeight.source === "backend" ? "Live Feed" : "Demo Feed"}</span>
            <span className={`wm-pill ${liveWeight.stable ? "wm-pill-stable" : "wm-pill-pending"}`}>
              {liveWeight.stable ? "Stable Ready" : "Reading"}
            </span>
          </div>
        </header>

        <div className="wm-content">
          <form className="wm-main wm-panel" onSubmit={handleSubmit}>
            <div className="wm-weight-banner">
              <div>
                <p>Load</p>
                <p>Weight</p>
              </div>

              <div className="wm-weight-stack">
                <span className="wm-live-dot" />
                <h1 className={liveWeight.stable ? "is-stable" : ""}>{displayWeight}</h1>
                <small>{liveWeight.stable ? "Stable capture window open" : "Indicator syncing"}</small>
              </div>
            </div>

            <div className="wm-meta-row">
              <span>{formattedNow}</span>
              <label>
                <input
                  type="checkbox"
                  checked={formData.withCamera}
                  onChange={(event) => handleChange("withCamera", event.target.checked)}
                />{" "}
                With Camera
              </label>
            </div>

            <div className="wm-form-grid">
              <div className="wm-col">
                <label className="wm-row">
                  <span>TRUCK NO</span>
                  <input
                    type="text"
                    value={formData.truckNo}
                    onChange={(event) => handleChange("truckNo", event.target.value)}
                  />
                </label>
                {errors.truckNo ? <p className="wm-error">{errors.truckNo}</p> : null}

                <label className="wm-row">
                  <span>MATERIAL CODE</span>
                  <input
                    type="text"
                    value={formData.materialCode}
                    onChange={(event) => handleChange("materialCode", event.target.value)}
                  />
                </label>

                <label className="wm-row">
                  <span>CUSTOMER CODE</span>
                  <input
                    type="text"
                    value={formData.customerCode}
                    onChange={(event) => handleChange("customerCode", event.target.value)}
                  />
                </label>

                <label className="wm-row">
                  <span>CHARGES</span>
                  <input
                    type="number"
                    min="0"
                    value={formData.charges}
                    onChange={(event) => handleChange("charges", event.target.value)}
                  />
                </label>

                <label className="wm-row">
                  <span>MOBILE NO -1</span>
                  <input
                    type="text"
                    value={formData.mobile1}
                    onChange={(event) => handleChange("mobile1", event.target.value)}
                  />
                </label>
                {errors.mobile1 ? <p className="wm-error">{errors.mobile1}</p> : null}

                <label className="wm-row">
                  <span>MOBILE NO -2</span>
                  <input
                    type="text"
                    value={formData.mobile2}
                    onChange={(event) => handleChange("mobile2", event.target.value)}
                  />
                </label>

                <label className="wm-row">
                  <span>MOBILE NO -3</span>
                  <input
                    type="text"
                    value={formData.mobile3}
                    onChange={(event) => handleChange("mobile3", event.target.value)}
                  />
                </label>
              </div>

              <div className="wm-col">
                <label className="wm-row">
                  <span>SERIAL NO</span>
                  <input
                    type="text"
                    value={formData.serialNo}
                    onChange={(event) => handleChange("serialNo", event.target.value)}
                  />
                </label>

                <label className="wm-row">
                  <span>MATERIAL NAME</span>
                  <input
                    type="text"
                    value={formData.materialName}
                    onChange={(event) => handleChange("materialName", event.target.value)}
                  />
                </label>
                {errors.materialName ? <p className="wm-error">{errors.materialName}</p> : null}

                <label className="wm-row">
                  <span>CUSTOMER NAME</span>
                  <input
                    type="text"
                    value={formData.customerName}
                    onChange={(event) => handleChange("customerName", event.target.value)}
                  />
                </label>
                {errors.customerName ? <p className="wm-error">{errors.customerName}</p> : null}

                <label className="wm-row">
                  <span>LOAD WT</span>
                  <input
                    type="number"
                    min="0"
                    value={formData.loadWt}
                    onChange={(event) => handleChange("loadWt", event.target.value)}
                  />
                </label>

                <label className="wm-row">
                  <span>EMPTY WT</span>
                  <input
                    type="number"
                    min="0"
                    value={formData.emptyWt}
                    onChange={(event) => handleChange("emptyWt", event.target.value)}
                  />
                </label>

                <label className="wm-row">
                  <span>NETT WEIGHT</span>
                  <input type="number" min="0" value={formData.nettWeight} readOnly />
                </label>
              </div>
            </div>

            {saveMessage ? <p className="wm-save-message">{saveMessage}</p> : null}

            <div className="wm-actions">
              {actionButtons.map((button) => (
                <button
                  key={button.label}
                  type={button.type}
                  className={`wm-action-btn ${button.tone}`}
                  disabled={isSaving && button.type === "submit"}
                  onClick={button.type === "button" ? () => handleAction(button.label) : undefined}
                >
                  {button.type === "submit" && isSaving ? "SAVING..." : button.label}
                </button>
              ))}
            </div>
          </form>

          <aside className="wm-side wm-panel">
            <h3>User Log - [a] : {logDate}</h3>

            <div className="wm-camera">
              {cameraFeeds.map((camera) => (
                <div key={camera.id} className="cam-frame">
                  <span className="cam-badge">{camera.status}</span>
                  <div className="cam-copy">
                    <p>{camera.title}</p>
                    <small>{camera.description}</small>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
