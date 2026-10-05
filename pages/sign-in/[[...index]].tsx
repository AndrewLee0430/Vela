import { SignIn } from '@clerk/nextjs';
import ArchivedFeatureNotice from '../../components/ArchivedFeatureNotice';
import { ARCHIVE_MODE } from '../../utils/archiveMode';

export default function SignInPage() {
  // Archive car (2026-10-05): no new sessions in an archive-mode build.
  if (ARCHIVE_MODE) return <ArchivedFeatureNotice />;
  return (
    <div className="min-h-screen flex items-center justify-center bg-app-bg">
      <SignIn
        routing="path"
        path="/sign-in"
        signUpUrl="/sign-up"
        fallbackRedirectUrl="/research"
      />
    </div>
  );
}
