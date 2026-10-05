import { SignUp } from '@clerk/nextjs';
import ArchivedFeatureNotice from '../../components/ArchivedFeatureNotice';
import { ARCHIVE_MODE } from '../../utils/archiveMode';

export default function SignUpPage() {
  // Archive car (2026-10-05): no new accounts in an archive-mode build.
  if (ARCHIVE_MODE) return <ArchivedFeatureNotice />;
  return (
    <div className="min-h-screen flex items-center justify-center bg-app-bg">
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        fallbackRedirectUrl="/research"
      />
    </div>
  );
}
