"use client";

import React from "react";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dna,
  FlaskConical,
  Activity,
  BarChart3,
  AlertCircle,
} from "lucide-react";

export default function AuthPage() {
  const router = useRouter();
  const { user, isLoading, login, register } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [registerError, setRegisterError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && user) {
      router.push("/dashboard");
    }
  }, [user, isLoading, router]);

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    setLoginError(null);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    const result = await login(email, password);

    if (result.success) {
      router.push("/dashboard");
    } else {
      const errorMsg = result.error || "Login failed";
      setLoginError(errorMsg);
    }

    setIsSubmitting(false);
  };

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    setRegisterError(null);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;
    const confirmPassword = formData.get("confirmPassword") as string;

    if (password !== confirmPassword) {
      const errorMsg = "Passwords do not match";
      setRegisterError(errorMsg);
      setIsSubmitting(false);
      return;
    }

    const result = await register(email, password);

    if (result.success) {
      router.push("/dashboard");
    } else {
      const errorMsg = result.error || "Registration failed";
      setRegisterError(errorMsg);
    }

    setIsSubmitting(false);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (user) {
    return null;
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Left side - Branding */}
      <div className="lg:flex-1 bg-primary p-8 lg:p-12 flex flex-col justify-between text-primary-foreground">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Dna className="h-8 w-8" />
            <h1 className="text-2xl font-bold tracking-tight">DE Portal</h1>
          </div>
          <p className="text-primary-foreground/80 text-sm">
            Direct Evolution Monitoring System
          </p>
        </div>

        <div className="hidden lg:block space-y-8 my-12">
          <div className="flex items-start gap-4">
            <div className="p-2 rounded-lg bg-primary-foreground/10">
              <FlaskConical className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">Experiment Staging</h3>
              <p className="text-sm text-primary-foreground/70">
                Integrate with UniProt API and validate plasmid sequences for
                your protein engineering experiments.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="p-2 rounded-lg bg-primary-foreground/10">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">Real-time Analysis</h3>
              <p className="text-sm text-primary-foreground/70">
                DNA-to-protein translation, mutation classification, and unified
                activity scoring.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="p-2 rounded-lg bg-primary-foreground/10">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">Visual Insights</h3>
              <p className="text-sm text-primary-foreground/70">
                Interactive charts showing activity distributions, top
                performers, and mutation fingerprints.
              </p>
            </div>
          </div>
        </div>

        <p className="text-xs text-primary-foreground/60 hidden lg:block">
          Designed for the Design-Build-Test-Learn cycle in automated protein
          engineering.
        </p>
      </div>

      {/* Right side - Auth forms */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 bg-background">
        <Card className="w-full max-w-md border-0 shadow-lg">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl">Welcome</CardTitle>
            <CardDescription>
              Sign in to your account or create a new one
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="login">Sign In</TabsTrigger>
                <TabsTrigger value="register">Register</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-4">
                  {loginError && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{loginError}</AlertDescription>
                    </Alert>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="login-email">Email</Label>
                    <Input
                      id="login-email"
                      name="email"
                      type="email"
                      placeholder="researcher@lab.edu"
                      required
                      autoComplete="email"
                      disabled={isSubmitting}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password">Password</Label>
                    <Input
                      id="login-password"
                      name="password"
                      type="password"
                      required
                      autoComplete="current-password"
                      disabled={isSubmitting}
                    />
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "Signing in..." : "Sign In"}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="register">
                <form onSubmit={handleRegister} className="space-y-4">
                  {registerError && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{registerError}</AlertDescription>
                    </Alert>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="register-email">Email</Label>
                    <Input
                      id="register-email"
                      name="email"
                      type="email"
                      placeholder="researcher@lab.edu"
                      required
                      autoComplete="email"
                      disabled={isSubmitting}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-password">Password</Label>
                    <Input
                      id="register-password"
                      name="password"
                      type="password"
                      required
                      minLength={6}
                      autoComplete="new-password"
                      disabled={isSubmitting}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-confirm">Confirm Password</Label>
                    <Input
                      id="register-confirm"
                      name="confirmPassword"
                      type="password"
                      required
                      minLength={6}
                      autoComplete="new-password"
                      disabled={isSubmitting}
                    />
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "Creating account..." : "Create Account"}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>

            <p className="text-xs text-muted-foreground text-center mt-6">
              Authenticated sessions are stored securely and last 24 hours.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
