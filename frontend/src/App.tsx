import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth, RequireRole } from "@/components/RequireAuth";
import Login from "@/pages/Login";
import Home from "@/pages/Home";
import Roster from "@/pages/Roster";
import Recon from "@/pages/Recon";
import Plan from "@/pages/Plan";
import Forecast from "@/pages/Forecast";
import HrSettings from "@/pages/hr/Settings";
import CareersLayout from "@/pages/CareersLayout";
import { StubPage } from "@/pages/StubPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route path="/careers" element={<CareersLayout />}>
        <Route index element={<StubPage title="Open roles" description="Published postings will be listed here." />} />
        <Route
          path=":slug"
          element={<StubPage title="Job details" description="Posting detail and application form land here." />}
        />
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
        <Route path="/requests" element={<StubPage title="Requests" description="Your submitted requests land here." />} />
        <Route path="/requests/new" element={<StubPage title="New request" description="The request form lands here." />} />
        <Route path="/requests/:id" element={<StubPage title="Request detail" description="Request detail and approval trail land here." />} />
        <Route path="/forecast" element={<Forecast />} />
        <Route path="/plan" element={<Plan />} />
        <Route path="/vendors" element={<StubPage title="Vendors" description="Vendor engagement overview lands here." />} />
        <Route path="/history" element={<StubPage title="History" description="Closed-cycle history lands here." />} />

        <Route
          path="/hr/inbox"
          element={
            <RequireRole role="HR">
              <StubPage title="Approval inbox" description="Pending requests awaiting HR decision land here." />
            </RequireRole>
          }
        />
        <Route
          path="/hr/postings"
          element={
            <RequireRole role="HR">
              <StubPage title="Postings" description="Manage job postings here." />
            </RequireRole>
          }
        />
        <Route
          path="/hr/applications"
          element={
            <RequireRole role="HR">
              <StubPage title="Applications" description="Review applicants here." />
            </RequireRole>
          }
        />
        <Route
          path="/hr/vendor-dispatch"
          element={
            <RequireRole role="HR">
              <StubPage title="Vendor dispatch" description="Send engagement confirmations to vendors here." />
            </RequireRole>
          }
        />
        <Route
          path="/hr/vendors"
          element={
            <RequireRole role="HR">
              <StubPage title="Vendor companies" description="Manage vendor company records here." />
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
