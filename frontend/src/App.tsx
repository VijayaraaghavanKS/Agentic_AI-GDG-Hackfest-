import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Market } from "@/pages/Market";
import { Analyze } from "@/pages/Analyze";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="market" element={<Market />} />
          <Route path="analyze" element={<Analyze />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
