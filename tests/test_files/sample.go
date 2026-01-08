// Sample Go file for parser tests

package main

import "fmt"

type Widget struct {
    Name string
}

func (w *Widget) Greet() string {
    fmt.Println("hi")
    return "hello"
}

func add(a int, b int) int {
    return a + b
}
