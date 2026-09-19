import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth, RequireRole } from "@/components/RequireAuth";
import Login from "@/pages/Login";
import Home from "@/pages/Home";
import Roster from "@/pages/Roster";
import Recon from "@/pages/Recon";
import Plan from "@/pages/Plan";
import Forecast from "@/pages/Forecast";
import Requests from "@/pages/Requests";
import RequestNew from "@/pages/RequestNew";
import RequestDetail from "@/pages/RequestDetail";
import Vendors from "@/pages/Vendors";
import HrSettings from "@/pages/hr/Settings";
import HrInbox from "@/pages/hr/Inbox";
import HrPostings from "@/pages/hr/Postings";
import HrApplications from "@/pages/hr/Applications";
import HrVendorDispatch from "@/pages/hr/VendorDispatch";
import HrVendorCompanies from "@/pages/hr/VendorCompanies";
import CareersLayout from "@/pages/CareersLayout";
import CareersList from "@/pages/careers/CareersList";
import CareersDetail from "@/pages/careers/CareersDetail";
import History from "@/pages/History";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route path="/careers" element={<CareersLayout />}>
        <Route index element={<CareersList />} />
        <Route path=":slug" element={<CareersDetail />} />
      </Route>

      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/home" element={<Home />} />
        <Route path="/roster" element={<Roster />} />
        <Route path="/recon" element={<Recon />} />
        <Route path="/requests" element={<Requests />} />
        <Route path="/requests/new" element={<RequestNew />} />
        <Route path="/requests/:id" element={<RequestDetail />} />
        <Route path="/forecast" element={<Forecast />} />
        <Route path="/plan" element={<Plan />} />
        <Route path="/vendors" element={<Vendors />} />
        <Route path="/history" element={<History />} />

        <Route
          path="/hr/inbox"
          element={
            <RequireRole role="HR">
              <HrInbox />
            </RequireRole>
          }
        />
        <Route
          path="/hr/postings"
          element={
            <RequireRole role="HR">
              <HrPostings />
            </RequireRole>
          }
        />
        <Route
          path="/hr/applications"
          element={
            <RequireRole role="HR">
              <HrApplications />
            </RequireRole>
          }
        />
        <Route
          path="/hr/vendor-dispatch"
          element={
            <RequireRole role="HR">
              <HrVendorDispatch />
            </RequireRole>
          }
        />
        <Route
          path="/hr/vendors"
          element={
            <RequireRole role="HR">
              <HrVendorCompanies />
            </RequireRole>
          }
        />
        <Route
          path="/hr/settings"
          element={
            <RequireRole role="HR">
              <HrSettings />
            </RequireRole>
          }
        />
      </Route>

      <Route path="/" element={<Navigate to="/home" replace />} />
      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  );
}
