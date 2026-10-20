import { useForm } from "@tanstack/react-form";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Check, XCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "../../components/common/Button";
import { Input } from "../../components/common/Input";
import { useCreateTodo } from "../../hooks/mutations/todos";
import { todoSchema } from "../../models/todo";
import { getErrorMessage } from "../../utils/helper";

/**
 * The Todo Creation feature page.
 * Provides an interface to create new todos with real-time form validation.
 */
export function TodoNew() {
  const [activeField, setActiveField] = useState<string | null>(null);
  const navigate = useNavigate();
  const { mutateAsync: createTodo } = useCreateTodo();

  const form = useForm({
    defaultValues: {
      title: "",
      description: "",
    },
    onSubmit: async ({ value }) => {
      try {
        await createTodo(value);
        toast.success("Todo created", {
          description: `"${value.title}" has been added to your list.`,
        });
        navigate({ to: "/todos" });
      } catch {
        toast.error("Failed to create todo");
      }
    },
  });

  const buttonStyle =
    "px-6 py-2.5 rounded-xl text-base shadow-md hover:shadow-lg transition-all shrink-0 font-bold uppercase tracking-wider";

  return (
    <main className="flex-1 px-10 py-8 max-w-5xl w-full mx-auto animate-fade-in">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          e.stopPropagation();
          form.handleSubmit();
        }}
      >
        <div className="mb-6">
          <Link to="/todos">
            <Button
              type="button"
              className={`${buttonStyle} bg-brand-200/50 text-gray-700 hover:bg-brand-400 hover:text-white border-none transition-all flex items-center justify-center gap-2`}
            >
              <ArrowLeft size={18} />
              Back
            </Button>
          </Link>
        </div>

        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border-2 border-brand-200/50">
          <div className="px-8 pb-8 pt-6">
            <form.Field
              name="title"
              validators={{
                onChangeAsync: todoSchema.shape.title,
                onChangeAsyncDebounceMs: 300,
              }}
            >
              {(field) => (
                <div className="mb-0 w-full">
                  <Input
                    variant="ghost"
                    type="text"
                    id={field.name}
                    name={field.name}
                    value={field.state.value}
                    onFocus={() => setActiveField(field.name)}
                    onBlur={() => {
                      field.handleBlur();
                      setActiveField(null);
                    }}
                    onChange={(e) => field.handleChange(e.target.value)}
                    className="text-5xl font-bold text-gray-700 placeholder:text-gray-400/60 pt-0 pb-2 leading-normal border-none bg-transparent outline-none focus:ring-0 shadow-none px-0"
                    placeholder="Title"
                    // eslint-disable-next-line jsx-a11y/no-autofocus -- primary field of a dedicated "new todo" page
                    autoFocus
                    error={
                      activeField === field.name &&
                      !field.state.meta.isValidating
                        ? getErrorMessage(field.state.meta.errors[0])
                        : undefined
                    }
                  />
                </div>
              )}
            </form.Field>

            <form.Field
              name="description"
              validators={{
                onChangeAsync: todoSchema.shape.description.unwrap(),
                onChangeAsyncDebounceMs: 300,
              }}
            >
              {(field) => (
                <div className="mb-4 relative">
                  {activeField === field.name &&
                    !field.state.meta.isValidating &&
                    field.state.meta.errors[0] && (
                      <span className="absolute -top-6 right-0 text-xs font-bold text-red-500 animate-slide-down">
                        {getErrorMessage(field.state.meta.errors[0])}
                      </span>
                    )}
                  <textarea
                    id={field.name}
                    name={field.name}
                    value={field.state.value}
                    onFocus={() => setActiveField(field.name)}
                    onBlur={() => {
                      field.handleBlur();
                      setActiveField(null);
                    }}
                    onChange={(e) => field.handleChange(e.target.value)}
                    placeholder="Tell your story..."
                    className={`w-full min-h-[300px] outline-none py-0 transition-all bg-transparent font-bold text-gray-700 text-xl placeholder:text-gray-400/60 resize-none leading-relaxed`}
                  />
                </div>
              )}
            </form.Field>
          </div>
        </div>

        <div className="mt-8 mb-12 flex justify-end gap-5">
          <Link to="/todos">
            <Button
              type="button"
              variant="primary"
              className={`${buttonStyle} bg-brand-200/50 text-gray-700 hover:bg-red-500 hover:text-white border-none group transition-all flex items-center justify-center gap-0 hover:gap-3`}
            >
              <span className="font-bold uppercase tracking-wider">Cancel</span>
              <XCircle
                size={18}
                className="w-0 group-hover:w-5 opacity-0 group-hover:opacity-100 transition-all duration-300 transform scale-0 group-hover:scale-100"
              />
            </Button>
          </Link>

          <form.Subscribe
            selector={(state) => [state.canSubmit, state.isSubmitting]}
          >
            {([canSubmit, isSubmitting]) => (
              <Button
                type="submit"
                disabled={!canSubmit || isSubmitting}
                variant="primary"
                className={`${buttonStyle} bg-brand-200/50 text-gray-700 hover:bg-green-600 hover:text-white border-none group transition-all flex items-center justify-center gap-0 hover:gap-3 disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <span className="font-bold uppercase tracking-wider">
                  {isSubmitting ? "Creating..." : "Create Todo"}
                </span>
                {!isSubmitting && (
                  <Check
                    size={20}
                    className="w-0 group-hover:w-6 opacity-0 group-hover:opacity-100 transition-all duration-300 transform scale-0 group-hover:scale-100"
                  />
                )}
              </Button>
            )}
          </form.Subscribe>
        </div>
      </form>
    </main>
  );
}
