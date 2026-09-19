import { Outlet } from "react-router-dom";

/** Public careers pages have no sidebar/auth — anyone can browse postings. */
export default function CareersLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border/70 bg-card/90 px-6 py-5 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="font-logotype text-xl font-medium tracking-tight text-foreground">HeadcountHQ</span>
          <span className="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground">Careers</span>
        </div>
      </header>
      <main className="flex-1 px-4 py-10 sm:px-6 lg:py-14">
        <Outlet />
      </main>
      <footer className="border-t border-border/70 bg-card px-6 py-6 text-center text-xs text-muted-foreground">
        Build the teams that move work forward.
      </footer>
    </div>
  );
}
