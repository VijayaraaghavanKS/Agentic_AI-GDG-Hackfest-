import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Market } from "@/pages/Market";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="market" element={<Market />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
