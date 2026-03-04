"use client";

import { Todo } from "@/lib/api";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatDate, isOverdue } from "@/lib/utils";
import { Check, Trash2, Edit2, Calendar } from "lucide-react";
import { clsx } from "clsx";

interface TodoCardProps {
  todo: Todo;
  onToggle: (id: number) => void;
  onDelete: (id: number) => void;
  onEdit: (todo: Todo) => void;
}

const priorityColors = {
  low: "bg-green-100 text-green-700 border-green-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  high: "bg-red-100 text-red-700 border-red-200",
};

export function TodoCard({ todo, onToggle, onDelete, onEdit }: TodoCardProps) {
  const overdue = !todo.is_completed && isOverdue(todo.due_date);

  return (
    <Card
      className={clsx(
        "transition-all hover:shadow-md",
        todo.is_completed && "opacity-60"
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <button
            onClick={() => onToggle(todo.id)}
            className={clsx(
              "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors",
              todo.is_completed
                ? "bg-primary border-primary text-primary-foreground"
                : "border-input hover:border-primary"
            )}
          >
            {todo.is_completed && <Check className="h-3 w-3" />}
          </button>

          <div className="flex-1 min-w-0">
            <h3
              className={clsx(
                "font-medium",
                todo.is_completed && "line-through text-muted-foreground"
              )}
            >
              {todo.title}
            </h3>

            {todo.description && (
              <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                {todo.description}
              </p>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span
                className={clsx(
                  "text-xs px-2 py-0.5 rounded-full border font-medium",
                  priorityColors[todo.priority]
                )}
              >
                {todo.priority}
              </span>

              {todo.due_date && (
                <span
                  className={clsx(
                    "text-xs flex items-center gap-1",
                    overdue
                      ? "text-red-600 font-medium"
                      : "text-muted-foreground"
                  )}
                >
                  <Calendar className="h-3 w-3" />
                  {formatDate(todo.due_date)}
                  {overdue && " (Overdue)"}
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>

      <CardFooter className="px-4 pb-4 pt-0 flex gap-2 justify-end">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onEdit(todo)}
          className="h-8 w-8"
        >
          <Edit2 className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onDelete(todo.id)}
          className="h-8 w-8 text-destructive hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
