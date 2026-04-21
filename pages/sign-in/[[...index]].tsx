import { SignIn } from '@clerk/nextjs';

const BG = 'linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)';

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: BG }}>
      <SignIn
        routing="path"
        path="/sign-in"
        signUpUrl="/sign-up"
        fallbackRedirectUrl="/research"
      />
    </div>
  );
}
