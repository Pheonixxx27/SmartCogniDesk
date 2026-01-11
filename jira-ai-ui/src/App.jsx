import { useState } from "react";
import Layout from "./components/Layout";
import TopBar from "./components/TopBar";
import BusinessDashboard from "./components/BusinessDashboards";
import DevDashboard from "./components/DevDashboard";

function App() {
  const [tab, setTab] = useState("business");

  return (
    <Layout>
      <TopBar tab={tab} setTab={setTab} />
      {tab === "business" && <BusinessDashboard />}
      {tab === "dev" && <DevDashboard />}
    </Layout>
  );
}

export default App;
