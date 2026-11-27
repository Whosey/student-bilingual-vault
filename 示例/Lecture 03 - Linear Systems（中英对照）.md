---
kind: "reading"
title: "Lecture 03 - Linear Systems"
course: "[[示例/线性代数（示例）]]"
status: "已完成"
page_count: 2
---

# Lecture 03 - Linear Systems（中英对照）

[[示例/Lecture 03 - Linear Systems.pdf|打开原 PDF]]

## 第 1 页

[[示例/Lecture 03 - Linear Systems.pdf#page=1|打开原 PDF 第 1 页]]

<!-- study:page 1 done -->

Lecture 03 - Linear Systems

第 3 讲 · 线性方程组

Equations and solutions

方程与解

A linear system is a set of linear equations in the same variables.

线性方程组（linear system）是由含有同一组变量的若干线性方程组成的。

A solution is an assignment of values that makes every equation true at the same time.

一组变量的取值若能同时满足每一个方程，就称为这个方程组的一个解。

The equations x + y = 5 and x - y = 1 have the solution x = 3, y = 2. Adding the equations gives 2x = 6.

方程 x + y = 5 和 x − y = 1 的解是 x = 3、y = 2。将两个方程相加，可以得到 2x = 6。


## 第 2 页

[[示例/Lecture 03 - Linear Systems.pdf#page=2|打开原 PDF 第 2 页]]

<!-- study:page 2 done -->

Pivots and free variables

主元与自由变量

A pivot marks a leading entry in a row after row reduction. Its column identifies a pivot variable.

行化简后，主元（pivot）位于某行的首个非零项。它所在的列对应一个主元变量。

A variable whose column has no pivot is called a free variable. If the system is consistent, changing a free variable can produce other solutions.

如果某个变量对应的列没有主元，就称它为自由变量（free variable）。如果方程组有解，给自由变量取不同的值，可以得到不同的解。

For x + y = 5, you can choose y first and then set x = 5 - y. Choosing y = 1 gives x = 4, and choosing y = 2 gives x = 3.

对 x + y = 5，可以先选定 y，再令 x = 5 − y。取 y = 1 时，x = 4。取 y = 2 时，x = 3。


## 我的疑问

- 第 2 页说可以先任选 y。若加上条件 x − y = 1，y 还可以自由取值吗？
